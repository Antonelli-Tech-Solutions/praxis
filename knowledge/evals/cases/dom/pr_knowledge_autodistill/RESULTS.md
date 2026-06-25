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

## Cost: knowledge pays only when the blind agent flails

Auto was cheaper on **only** `yoyo` (−233 tokens) — the one footgun where the blind control flails
(repeated failed runs against the crash). On `delete` (+235) and `umap` (+274) the blind agent
already produces *a* working artifact cheaply, so the injected facts are processing overhead the
control never paid. Consistent across both runs: the token benefit materializes only on a footgun
that actually traps the blind agent.

## What's now settled vs open

- **Two validated footguns** (yoyo control 2/3, delete control 3/3) — the single-footgun
  provisional caveat is **resolved**; the NO-GO is no longer hostage to one construct.
- **Open — extraction quality.** The delete result says auto-distillation's *phrasing* is the
  bottleneck for soft constraints. The lever is the distiller (R2 prompt): capture the actionable
  guard, not just the durable-policy sentence. A cheap next experiment: re-distill the delete PR
  with a prompt that demands the concrete code form, and re-run the delete auto arm.
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

## Next increment

1. **Improve the distiller for actionable extraction** (the EXTRACTION-QUALITY lever) — highest-value
   and cheapest: the delete footgun already isolates it. Re-distill targeting the code guard, re-run
   the delete auto arm, see if it then flips.
2. **Scope-aware retrieval** (the umap ranking lever) — the parent proposal's next slice
   (write-path provenance + scope reader); now data-justified. Warrants its own plan.
3. **Establish the dogfood "does knowledge help at all" premise** before any GO here is trusted.

*Raw records, diagnostics (incl. `surfaced_trials`), per-arm aggregates, and gate in
`RESULTS.data.json`.*
