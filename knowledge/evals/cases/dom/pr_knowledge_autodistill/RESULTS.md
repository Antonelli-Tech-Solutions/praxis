# PR-knowledge auto-distill slice — results

**Run:** 2026-06-25 · two-footgun run: 3 tasks (2 gating + 1 cost-signal) × 3 trials ×
{auto, control, (+curated on gating tasks)} = 24 real Claude Code runs · distiller
`openai/gpt-4o-mini`, embeddings `openai/text-embedding-3-small` (replayed from cache).

> **History.** A first run (1 gating footgun) reported GO (provisional); code review found a
> case-id collision that had it measuring the wrong arm — corrected to NO-GO. A second footgun
> (`delete_active_guard`) was then validated (blind control 3/3) and added, so the gate now rests
> on **two** validated footguns. This is that two-footgun run.

## Verdict: **NO-GO** — but the finding is the *contrast* between the two footguns

The two validated footguns give **opposite** knowledge-value outcomes, and that split is the
result worth keeping:

| Footgun | constraint type | auto avoids | control exhibits | flip | curated | token Δ (auto vs control) |
|---------|-----------------|-------------|------------------|------|---------|---------------------------|
| **`yoyo_lazy_import`** | **hard** — wrong code raises `ModuleNotFoundError` | **3/3** | 2/3 | ✅ | 3/3 | **−233 (cheaper)** |
| **`delete_active_guard`** | **soft** — unguarded `DELETE` runs fine, deletes `active` facts | **0/3** | 3/3 | ❌ | 2/3 | +235 (dearer) |
| `umap_neighbors` (cost-signal) | — | 3/3 | 3/3¹ | (non-gating) | — | +274 (dearer) |

Gate: NO-GO — `delete_active_guard` did not flip, and auto cut tokens on only 1/3 tasks.

¹ umap's control exhibit-rate swung **0/3 (prior run) → 3/3 (this run)** — the stark run-to-run
variance that got it demoted to a non-gating cost signal. Vindicated.

## The headline: auto-distillation works for *hard* constraints, loses the actionable form for *soft* ones

All three neutralizing facts were **extracted into the artifact and retrieved 3/3** (R7 inputs all
green — see diagnostics). So the difference between yoyo and delete is **not** extraction-presence
or retrieval — it is the *distilled phrasing*, isolated by the curated ceiling:

- **`yoyo` (hard constraint).** The distilled fact — *"yoyo executes migrations with the repo root
  off sys.path, necessitating lazy imports"* — is actionable enough: the wrong code **crashes**, so
  the agent must comply, and it defers the import 3/3. Auto-distill+retrieve **works here**.
- **`delete` (soft policy).** The distilled fact — *"deletion of facts is gated to only
  'proposed'/'rejected' states"* — describes the **policy**, and the agent reads it but still writes
  an unguarded `DELETE ... WHERE id = %s` **0/3**: nothing crashes, so the policy reads as
  informational. The **curated ideal fact**, which carries the *actionable code* (`AND state IN
  ('proposed','rejected')`), flips it **2/3**. R7 therefore attributes the shortfall to
  **EXTRACTION-QUALITY** — curation retains an actionable form that `gpt-4o-mini`'s descriptive
  distillation drops.

This is the first time the R7 three-way machinery produced an **EXTRACTION-QUALITY** verdict, and it
is the experiment's most actionable signal: **the distiller should extract the actionable guard/code,
not just the policy prose** — especially for soft constraints an agent can ignore without an error.
It also validates the curated-ceiling design (it cleanly split "knowledge has no value" from
"auto-distillation lost the value curation keeps").

### 2×2 confirmation — it is phrasing, not dilution (6-trial probe)

EXTRACTION-QUALITY conflates two variables — *phrasing* (policy prose vs actionable guard) and
*dilution* (1 injected fact vs 8). The auto (weak+diluted) and curated (ideal+isolated) cells only
sit on the diagonal, so a 2×2 with both off-diagonal cells decomposes it:

| (guard rate /3) | weak phrasing (distilled) | ideal phrasing (curated) |
|-----------------|---------------------------|--------------------------|
| **isolated** (1 fact, whole-file) | **0/3** (Arm C) | 2/3 (curated) |
| **diluted** (8 retrieved) | 0/3 (auto) | **3/3** (Arm D) |

- **Phrasing effect: decisive.** Ideal phrasing flips (2/3, 3/3); weak phrasing never does (0/3, 0/3).
- **Dilution effect: ~none.** Ideal phrasing survives 7 distractors *fine* (diluted 3/3 ≥ isolated
  2/3 — the gap is n=3 noise); weak fails whether alone or diluted.

So the bottleneck is unambiguously the **distilled phrasing**, not injection/ranking. (This is a
*different* bottleneck than `umap`, whose fact retrieves and avoids fine but is a retrieval *cost*
problem from ranking — so the distiller lever and the scope-ranking lever address different axes and
do not compete.) Arms `delete_active_guard_{weak_isolated,ideal_diluted}` carry this probe.

## Cost: knowledge pays only when the blind agent flails

Auto was cheaper on **only** `yoyo` (−233 tokens) — the one footgun where the blind control flails
(repeated failed runs against the crash). On `delete` (+235) and `umap` (+274) the blind agent
already produces *a* working artifact cheaply, so the injected facts are processing overhead the
control never paid. Consistent across both runs: the token benefit materializes only on a footgun
that actually traps the blind agent.

## What's now settled vs open

- **Two validated footguns** (yoyo control 2/3, delete control 3/3) — the single-footgun
  provisional caveat is **resolved**; the NO-GO is no longer hostage to one construct.
- **Settled — extraction quality (the lever was run; see "EXTRACTION-QUALITY lever" below).** The
  distiller prompt now folds in the concrete enforcement form; it ships, validated with no
  yoyo/umap regression. But the upside is **bounded by two ceilings** — source-layer fidelity and
  footgun availability — so the delete footgun moved only 0/3 → 1/3, not to the curated 2–3/3.
- **Open — scope-aware retrieval.** Still motivated by the umap rank probe (neutralizing fact ranks
  #6 under repo-scoped distractors; a scope-match boost lifts it to #2). Independent of the
  extraction-quality finding; it's the parent's next slice (needs write-path provenance + a
  scope-aware reader). See the rank-probe section below.

## Follow-up analysis — the umap cost is a ranking gap (offline probe)

The umap regression is a **ranking** failure, not over-injection: the `n_neighbors` fix ranks **#6**
of 8 injected, out-scored by 5 `repo`-scoped clustering distractors (cluster-id stability,
super-nodes…) at 0.47–0.50 vs the fix at 0.42. Tightening `top_k` would *drop* the fix (top_k<6
loses it) — so the over-injection is "must inject 5 distractors to reach the rank-6 fact." The facts
carry the scope to fix it (`scope=file:knowledge/knowledge_graph/clustering.py`; the task edits
`clustering.py`); an offline scope-match boost (+0.15 for a file-scoped fact matching the task
target) re-ranks the fix **#6→#2 (umap)** / **#2→#1 (yoyo)**. That is the retrieval-attributed
evidence motivating scope-aware retrieval.

## The EXTRACTION-QUALITY lever — shipped, with its ceiling mapped

The 2×2 named *phrasing* as the delete bottleneck and pointed at the distiller. That lever was
built and run; the result is that it **works but is twice-bounded**, and the boundary is the real
finding.

**Part 1 — the distiller now folds in the enforcement form (shipped).** The R2 prompt was changed so
that, for a constraint on *how code must be written* (one an agent can violate without an error), the
fact carries the concrete enforcement form (guard/signature/call) as a brief illustrative example,
not policy prose alone. Validated by re-distilling the **same 31 sources** that produced the frozen
corpus:

- **No regression on the footgun facts** — re-running yoyo and umap against the re-distilled corpus
  held **3/3 each** (baseline 3/3). The yoyo fact in fact *improves*, folding in "import `connect`
  lazily within the local CLI `main()`".
- **No bloat** — 154 → 157 facts, mean length 195 → 215 chars.
- **The delete fact gains its real enforcement form** — re-distilling PR #41 now yields *"…enforced
  by returning a 409 error if an attempt is made to delete an 'active' fact"*. The diluted auto arm
  moves **0/3 → 1/3** (n=3, so ≈ baseline) — still well short of the curated SQL-guard ideal (2/3
  isolated, 3/3 diluted).

**Ceiling 1 — source-layer fidelity.** The distiller can only fold in the enforcement the source PR
*contains*. PR #41 enforces deletion-gating at the **API layer (a 409)**, but the task writes **raw
psycopg SQL** — so the captured 409 form doesn't transfer; the agent bridges 409 → `WHERE … AND
state IN (…)` only 1/3 (trial 3 translated it to a `ValueError` on `'active'`; trials 1–2 wrote an
unguarded `DELETE`). The curated ideal flipped because a *human* wrote the guard at the task's layer
— a form PR #41's diff never contained.

**Ceiling 2 — footgun availability.** Looking for a footgun whose source enforces *at the task's
layer*, two candidates were validated and **both failed the blind control at 0/3**:

| candidate | weak fact | new enforcement form | blind exhibit |
|-----------|-----------|----------------------|---------------|
| #34 ingestion cassette key | "a deterministic cassette ensures consistent results" | `sha256(model_id + raw_input)` | **0/3** — agent always keyed on `model` |
| #40 eval cache key | "leaf-name keying rejected for the backend case id" | `c.caseId ?? leafName(c.scope)` | **0/3** — agent always used `caseId` |

Both failed for the **same structural reason**: a same-layer enforcement is only a *footgun* when its
value is **absent from the task signature**. `delete_fact(conn, fact_id)` exposes no `state`, so the
agent writes a complete *working* `DELETE` and the state restriction is a non-local rule it must
already know — that gap is the footgun. #34 hands the agent `model`; #40 hands it `caseId`; both are
correct-by-default, so neither is a footgun. A visible object-field/param can't be a footgun; only an
external constraint the signature doesn't surface (a DB column, a cross-cutting policy) qualifies.

**Conclusion.** The lever is real and shipped, but a clean large upside flip can't be demonstrated on
this corpus — not because the lever is wrong, but because the qualifying intersection (same-layer ∧
soft-policy ∧ genuinely-a-footgun) is structurally narrow. The delete footgun sits in it; almost
nothing else in the corpus does.

## Next increment

1. ~~**Improve the distiller for actionable extraction.**~~ **Done** (see above) — shipped and
   validated; the upside is ceiling-bounded, not a clean flip. A fairer upside test needs a footgun
   whose source enforces at the task's layer *and* whose enforcement value isn't in the task
   signature; such footguns are scarce and would have to be authored deliberately.
2. **Scope-aware retrieval** (the umap ranking lever) — the parent proposal's next slice
   (write-path provenance + scope reader); now data-justified. Warrants its own plan.
3. **Establish the dogfood "does knowledge help at all" premise** before any GO here is trusted.

*Raw records, diagnostics (incl. `surfaced_trials`), per-arm aggregates, and gate in
`RESULTS.data.json`.*
