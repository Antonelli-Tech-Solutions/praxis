# PR-knowledge auto-distill slice — results

**Run:** 2026-06-25 · 2 tasks × 3 trials × {auto, control, (+curated on the gating task)} =
15 real Claude Code runs · distiller `openai/gpt-4o-mini`, embeddings
`openai/text-embedding-3-small` (replayed from the committed cache).

## Verdict: **GO (provisional)**

Auto-distilled-and-retrieved PR knowledge produced a **dual-signal win on the gating footgun**:
the auto arm avoided the footgun every trial **and** spent ~40% fewer tokens than the no-facts
control — with both R7 diagnostics green (the neutralizing fact was extracted into the artifact
*and* surfaced by the retriever). It is **provisional** because the gate rests on a single
validated footgun whose control sat right at the exhibit bar, and the upstream "does knowledge
help at all" dogfood premise is still unestablished (see *Caveats*).

## Numbers

| Task | Arm | tokens (mean ± sd) | turns | footgun avoided |
|------|-----|--------------------|-------|-----------------|
| **`yoyo_lazy_import`** (gating) | auto | **2014 ± 102** | 7.0 | 3/3 |
| | control | 3344 | 9.0 | 1/3 (exhibited 2/3) |
| | curated ceiling | — | — | 3/3 |
| **`umap_neighbors`** (cost-signal) | auto | **1268 ± 39** | 4.3 | 3/3 |
| | control | 2367 | 5.0 | 3/3 (exhibited **0/3**) |

- **Gating footgun flip:** auto avoid-rate **1.00** ≥ 0.5 **and** control exhibit-rate **0.67**
  ≥ the 2/3 validity bar → **flip = True**. The curated ceiling also flipped (`curated_flip = True`).
- **Token/turn:** auto cheaper on **both** tasks (−1330 tokens / −2 turns on yoyo; −1100 / −0.7 on
  umap). Low spread (sd 102 / 39) — the reduction is consistent, not a single lucky trial.

## R7 attribution

The auto arm **flipped the gating footgun**, so there is **no shortfall to attribute** — the
three-way machinery (EXTRACTION / RETRIEVAL / KNOWLEDGE-VALUE) stays dormant by design. The two
upstream signals it consumes both came back positive:

- **Extraction ✓** — the neutralizing fact distilled cleanly into `facts.insights.json` for both
  tasks (yoyo: *"Yoyo executes migration files… repository root is not on sys.path, necessitating
  lazy imports to avoid ModuleNotFoundError"*; umap: *"…set UMAP's n_neighbors to 10 instead of
  15…"*).
- **Retrieval ✓** — the semantic-only reader surfaced that fact in the **top-15 of 154** seeded
  facts for the natural task query (offline probe + the live `injected_knowledge`). **The retrieval
  gap the parent proposal predicted did *not* bite on these tasks** — a finding in itself: the
  immediate, on-these-tasks motivation for two-lane scope-aware retrieval is weaker than expected.

The token/turn reduction is the cleanest signal and is **not** the metric-bias trap the dogfood
lesson warned about (first-pass volume crediting the control's cheap *wrong* output as free): here
the control spent **more** tokens **and** still hit the footgun, while the auto arm was cheaper
**and** correct. The token figure is output-dominated (the cache-read injected-knowledge block is
excluded from `input_tokens`), so it measures *agent work / flailing*, not knowledge payload — the
"fewer exploration turns" lever the dogfood single-file task failed to surface, surfaced here on
both a create-task (yoyo) and a repo-mounted task (umap).

## Caveats (why provisional)

1. **Single validated footgun.** Only `yoyo_lazy_import` gates, and its control exhibit-rate landed
   *exactly* at 2/3 — one trial's blind agent deferred the import on its own. A single control trial
   flipping the other way drops it below the bar. The verdict is one coin-flip from NO-GO.
2. **umap is a cost signal only.** Its control exhibited the footgun **0/3** (the blind agent kept
   n_neighbors low on its own every time), matching the dogfood v2 variance finding — so it
   contributes the (real, consistent) token/turn reduction but **no** footgun flip. Correctly
   non-gating.
3. **Upstream premise unestablished.** The dogfood "does curated knowledge help at all" gate is
   still NO-GO; this slice does not establish it, only that auto-distillation + retrieval recovers
   the curated arm's footgun-avoidance on the one task where the bet is validated.
4. **n = 3.** Small sample; the token deltas are large and low-variance, but the binary flip is the
   load-bearing signal and it is thin.

## Next increment

- **Add a second validated footgun** (the recommended strengthening) before treating any GO as
  firm — no other construct is validated yet, and inventing one blind would repeat the dropped-
  `phoenix` mistake. This is the single highest-value follow-up.
- **Scope-aware retrieval is *not* yet motivated by evidence.** Semantic-only retrieval surfaced the
  right fact top-15/154 here. Defer the two-lane work until a task produces a *retrieval-attributed*
  shortfall (fact present in the artifact but unsurfaced) — which this run did not.
- **Establish the dogfood premise** (≥2 reliably-blind-tempting footguns + a heavier repo-mounted
  task) so a future GO here is not provisional on an unproven upstream bet.

*Raw records, diagnostics, per-arm aggregates, and gate in `RESULTS.data.json`.*
