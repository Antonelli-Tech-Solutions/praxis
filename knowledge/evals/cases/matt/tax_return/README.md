# Tax-return evals (Matt)

Goal: prove the contract **"an external agent can offload its knowledge layer to
Praxis."** A hackathon-style tax-filing assistant should only have to drop its
documents in and ask for context; everything KG-shaped (distillation, dedup,
retrieval ranking) stays inside Praxis. This eval exercises that whole pipeline
on real TY2025 tax material: **raw 1040 instructions + W-2(s) + intake Q&A →
ingest/distil → retrieve → the agent fills the return → graded.**

## Design

Each scenario is a **full-pipeline case** (`component: null`):

1. **Raw ingestion.** The shared `sources/form_1040_instructions.txt` (line-by-line
   rules, TY2025 standard deductions, single/MFJ/HOH brackets) plus the scenario's
   own W-2(s) and intake Q&A (written into `sources/<slug>/`) are fed in raw
   through `seeded_insight.via_ingestor`. The ingestor distils them into the
   knowledge graph. We do **not** hand-write pre-distilled facts.
2. **A generic prompt is the query.** The `seed_prompt` just says "fill out the
   return" — it names no numbers. The agent must pull the W-2 amounts, the filing
   status / deduction choice from the Q&A, and the rules + brackets from the
   instructions out of the ingested knowledge, then do the arithmetic itself and
   write the completed return to `answer.md`.
3. **Grading.** `deterministic_checks` (`output_nonempty` + comma-optional
   `regex_matches` for total income, standard deduction, taxable income, computed
   tax, withholding, and the refund/owe bottom line, plus a `regex_absent` guard
   against fabricated credits) assert the figures land. A `rubric` grades
   grounding / arithmetic / completeness / honesty.

So the chain under test is: **raw docs → ingest/distil → retrieve → agent fills
the 1040 → graded.**

## Source of truth

All arithmetic is computed once, in `_generate.py`, so the deterministic-check
regexes and the rubric's arithmetic criterion can never drift from the canonical
figures. To change a scenario or the rules, edit `_generate.py` (or
`sources/form_1040_instructions.txt`) and re-run it — **do not hand-edit the
generated `case.yaml` files.**

```powershell
uv run python knowledge/evals/cases/matt/tax_return/_generate.py
```

## Scenarios (TY2025)

| Case (folder) | Filing status | Wages / withheld | Std deduction | Taxable | Tax | Bottom line |
|---|---|---|---|---|---|---|
| `single_w2` | Single | 40,000 / 3,200 | 15,750 | 24,250 | 2,672 | **refund 528** |
| `mfj_two_w2` | MFJ (two W-2s) | 40,000 + 35,000 = 75,000 / 5,800 | 31,500 | 43,500 | 4,743 | **refund 1,057** |
| `single_owes` | Single | 90,000 / 9,000 | 15,750 | 74,250 | 11,249 | **owes 2,249** |

- `single_w2` mirrors the hackathon taxpayer profile (single, one W-2, ~$40k/yr).
- `mfj_two_w2` forces the agent to aggregate two W-2 Box 1 amounts.
- `single_owes` is under-withheld, so it must land an **amount owed**, not a refund.

## Retrieval recall case (`retrieval_recall/`)

`matt_tax_return_retrieval_recall` is a `component: graph_reader` case. It
re-ingests the single-filer's docs and queries with a fill-the-return question,
then asserts the reader output surfaces the salient facts an agent needs —
wages (40,000), withholding (3,200), the 15,750 standard deduction, the `single`
filing status, and the "standard deduction" concept. This grades the **retrieval
set itself** (recall), not only the final answer, so retrieval can't be tuned on
answer quality alone.

## Ruleset-distillation integrity case (`ruleset_distillation/`)

`matt_tax_return_ruleset_distillation` is a `component: graph_reader` case that
ingests the **exact 26-doc `app/rules.py` `RULE_DOCUMENTS` corpus** the live
graph is seeded from (copied verbatim into `_generate.py`), through the **full
live-like write policy** (`merge_model` + `conflict_model` wire the LLM merge
judge and the claim/semantic conflict detectors), then asserts the reader
surfaces every salient fact an agent needs to file a 1040. It grew out of an
audit that found the distiller silently dropping filing-status brackets whose
numeric range collides across statuses (e.g. Single 22% merged into the MFS
twin), so the checks cover the **whole rule set**, not just the brackets:

- **Standard deduction** for all four statuses (label-bound; Single and MFS are
  both $15,750, so only the label binding distinguishes them).
- **Every bracket of every status's full 10%–37% ladder** (28 checks), each
  binding *filing-status label + rate + a characteristic dollar figure* within a
  single sentence, **order-independent** (distillation freely reorders
  "Single … 12% …" vs "12% … for single filers").
- The **marginal / sum-of-brackets** computation rule.
- The **W-2 box mappings** (box 1 → line 1a, box 2 → line 25a).
- The **Form 1040 line flow**: AGI (line 11), taxable income = line 11 − line 12
  floored at zero, refund (line 34) vs. amount owed (line 37), the "larger of
  standard or itemized" rule, and whole-dollar rounding.

Checks bind the status label because a bracket's bare *numbers* can survive via a
same-range twin in another status even when this status's own fact is dropped —
only a label-bound check catches that silent collapse.

### Status: RED — and what it caught (20/43 at time of writing)

Run against the pinned ingest cassette, the case **fails 23 of 43 checks**, and
every failure is a *genuine* dropped fact (verified: the missing dollar figures —
$31,500, $375,800, $17,000, $206,700, $394,600, $501,050, $250,500 — appear
nowhere in the distilled output). Of the **28 bracket facts, only ~8 survived**;
the MFJ standard deduction and the taxable-income floor ("never less than zero")
were also lost. So distilling the dense, cross-status-overlapping numeric corpus
through the merge+conflict policy is **heavily lossy** — the same class of defect
the audit found, at larger scale.

**Faithfulness caveat.** This offline policy is *harsher* than the live harness
`/ingest`: re-seeding the real harness (`POST /api/seed_kg`) into a clean org
keeps a near-complete graph (~62 facts, only Single 22% dropped), whereas this
eval's `merge_model`+`conflict_model` config (both `gpt-4o-mini`) collapses most
brackets. So treat the exact 20/43 as a **stress-configuration** signal, not a
1:1 reproduction of the deployed serve. The value is directional and regressive:
it pins, deterministically, which facts this policy preserves, so a distiller
change can be measured against it. Re-record the cassette
(`embed_cache --add` + a keyed run) after a distiller change to refresh the
baseline. To tighten faithfulness, pin the case's judge model/threshold to the
deployed serve's, or add an integration arm that drives the live `/ingest`
directly and asserts the full ladders survive.

## Full-pipeline knobs (per scenario)

Copied from `matt/applications`, with the same rationale:

- `substrate: vector` — real `VectorGraph` write policy (redact/dedup), not the
  in-memory stub.
- `embedder: cached` — committed real vectors that replay offline.
- `ingest_model: openai/gpt-4o-mini` — real LLM distillation, not passthrough.
- `ingest_state: active` — distilled facts land active + retrievable (the default
  `proposed` would be gated out of the reader).
- `reader: retrieving`, `reader_top_k: 0` — rank all active facts against the
  prompt with the volume cap off, so facts from all three docs compete together.
- `needs: [file_io]` — the agent writes `answer.md`; checks grade that text.
- `target_commit: 0*40`.

## Run

```powershell
# one scenario, real Claude Code — ingests, fills answer.md, grades
uv run python -m knowledge.evals.run matt_tax_return_single_w2
```

The full-pipeline scenarios need a file-producing agent (`needs: [file_io]`), so
the offline `--fake` backend **skips** them (there is no agent to write
`answer.md`). The `graph_reader` retrieval_recall case has no `file_io` need and
grades reader output directly.
