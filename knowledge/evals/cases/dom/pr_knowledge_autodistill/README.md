# PR-knowledge auto-distill slice — eval suite

Tests whether knowledge **auto-distilled** from merged PRs (one LLM call each, frozen
to an artifact) and **retrieved** through the existing semantic reader helps a coding
agent avoid documented footguns — and, when it falls short, *why*.

See the plan: `docs/plans/2026-06-24-002-feat-pr-knowledge-auto-distill-plan.md`.

## Arms

Every task is a paired set; the gating footgun adds a third ceiling arm.

| Arm | Seed | Reader | Asserts |
|-----|------|--------|---------|
| **auto** (`<task>`) | the frozen distilled facts (`facts.frozen.txt`) via `direct_to_graph` (active) | `retrieving` over a `vector` substrate + `cached` embeddings | footgun **absent** |
| **control** (`<task>_before`) | none (cold graph) | n/a | footgun **present** (positive-assertion) |
| **curated ceiling** (`<task>_curated`, gating task only) | the hand-written **ideal** fact via `direct_to_graph` (active) | `whole_file` (force-injected, no retrieval gate) | footgun **absent** |

The controls use the repo's **positive-assertion** convention (`pathlib_preference_before`):
they assert the blind-default footgun is *present*, so agent nondeterminism can't quietly
XPASS a meaningless green. Confirm each `_before` control genuinely **exhibits** the footgun
blind before trusting an auto/curated arm's avoidance — a control that dodges the footgun
proves nothing (measurement validity).

## Tasks

- **`yoyo_lazy_import`** — *the gating footgun* (PR `1fdb8be` / #48). Write a yoyo migration
  that calls into a `knowledge....` module. yoyo execs migration files with the repo root off
  `sys.path`, so the universal instinct — a top-level `from knowledge...` import — raises
  `ModuleNotFoundError` before the step runs; the neutralizing fact says import `knowledge`
  lazily inside the step. The dogfood v2 run validated this control fires **3/3** (clean flip).
  Check pair: control asserts a column-0 `^(?:from|import)\s+knowledge\b` is present
  (`text:regex_matches`); auto + curated assert it is absent (`text:regex_absent`). Mounts no
  `fixtures/` (pure create-task). **Gate on this footgun's flip.**

- **`umap_neighbors`** — *demoted to a non-gating cost signal* (PR `d892e88` / #57). Fix
  "topics collapse into one blob" in a mounted `clustering.py`. The blind instinct is to *raise*
  `n_neighbors` (backwards); the fact says keep it low. The dogfood run showed its control is
  variance-prone (exhibited 2/3 in v1, **0/3** in v2 — at n≈3 the flip is a coin-flip), so it
  earns its place on the **token/turn cost signal**, not on footgun-avoidance. Two arms, no
  curated ceiling.

`phoenix_tracing` was **dropped**: dogfood v2 proved its blind control never exhibited the
defect (0/3). Adding a *second* validated footgun is the recommended next strengthening — none
is validated yet, and inventing one blind would repeat the phoenix mistake.

## Frozen artifacts (produced by the one-shot backfill)

- `facts.frozen.txt` — the distilled fact texts; the **auto** arm seeds these.
- `facts.insights.json` — full `Insight` metadata (source/scope/category); R7 extraction reads it.

Regenerate (live; needs `gh auth` + `OPENROUTER_API_KEY`):

```sh
python -m knowledge.injestion.backfill_prs 30     # writes the two artifacts
python -m knowledge.evals.embed_cache --refresh   # re-embeds the new fact texts, commits the cache
```

The **auto-arm** `case.yaml`s (`yoyo_lazy_import/`, `umap_neighbors/`) are populated from
`facts.frozen.txt` after that backfill — their `direct_to_graph` seed is the frozen corpus, and
their `retrieving` reader needs the committed vectors. To keep retrieval *earned* and not
author-tuned, freeze the facts first, then write each task prompt from the natural user symptom,
not from the fact's vocabulary.

## Run

```sh
python knowledge/evals/cases/dom/pr_knowledge_autodistill/analyze.py --trials 3
```

Two arms per task (+ curated on `yoyo_lazy_import`), token/turn delta + the gating footgun's
flip, and — on a gating shortfall — a three-way attribution (EXTRACTION / RETRIEVAL /
KNOWLEDGE-VALUE, the last split from EXTRACTION-QUALITY by the curated ceiling). Any GO is
reported **provisional**.
