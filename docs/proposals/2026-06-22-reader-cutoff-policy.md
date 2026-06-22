# Proposal: `RetrievingReader` cutoff policy (top-k + relative cutoff + absolute floor)

**Owner:** Dominic Antonelli — eval harness / retrieval
**Status:** Proposed
**Date:** 2026-06-22
**Scope:** `knowledge/graph_reader` (`RetrievingReader`), and the reader-dependent eval cases it settles
**Builds on:** [2026-06-21-retrieving-reader-semantic-retrieval.md](2026-06-21-retrieving-reader-semantic-retrieval.md) (implemented)

> The `RetrievingReader` exists and works, but its cutoff is a **hardcoded absolute
> `min_score=0.35`** pinned to one embedding model — committed only as a *provisional*
> contract. This proposal decides the real policy: **`top_k` (volume cap) + a relative
> cutoff (keep what's close to the best hit) + a small absolute floor (is anything good
> enough at all)**. The relative piece makes it model-robust; the floor is what lets the
> negative-control cases honestly return nothing. Deciding this also reconciles the
> cluster of reader-dependent eval cases that currently bet on different answers.

---

## 1. Problem

`RetrievingReader.read` today filters to `score >= min_score` then caps at `top_k`,
with `lost_in_middle_reader` setting `min_score=0.35`. That value was calibrated
against `text-embedding-3-small`'s actual scores — which is exactly its weakness:

- **Model-pinned.** Cosine scales differ by embedding model; `0.35` separates
  relevant from irrelevant for *this* model and would need recalibration for any other.
- **Per-case, not a system contract.** It lives on the case, so it reads like a
  test-tuned knob rather than how the reader actually behaves. The case carries a
  `PROVISIONAL` note saying as much.
- **Absolute thresholds are brittle** generally (see §6) — too low admits noise, too
  high over-filters, and the right value drifts with corpus and model.

Meanwhile two degenerate alternatives are each wrong on their own:

- **Pure `top_k`** never drops irrelevant facts — it always returns *k*. On the reader
  graph, `top_k=8` returns CloudFront (rank 3) and X-Ray (rank 8), so the `excludes_*`
  checks fail. Top-k caps volume; it can't express "drop the junk."
- **Pure absolute threshold** is the brittle, model-pinned thing above.

We need a cutoff **policy** — a small set of global system constants — that is robust
across models and honest on the "nothing is relevant" case.

## 2. Grounding data (measured, `text-embedding-3-small`)

`lost_in_middle_reader`, query *"Add a TODO comment about adding caching…"*:

```
0.5162  Caching rule        (relevant — keep)
0.4500  TODO(MD) rule       (relevant — keep)
──────  largest gap (0.178)
0.2720  CloudFront          (irrelevant — drop)
0.2272  repository layer
0.1900  PRs/review
0.1850  type hints
0.1836  logging
0.1784  X-Ray               (irrelevant — drop)
 …
0.0622  SES                 (irrelevant — drop)
```

The relevant facts cluster at 0.45–0.52; the distractors sit ≤ 0.27, with a clean
**0.18 gap** between. Separately, a *no-relevant-fact* query (e.g.
`negative_control_irrelevant`: a CSS-only graph asked to write `add(a,b)`) produces a
top score around ~0.2 — there is no good match, and the right answer is **return
nothing**.

## 3. Criteria a good policy must meet

1. **Keep the relevant facts** (TODO + caching above).
2. **Drop the irrelevant-but-present** (CloudFront/X-Ray/SES) — this is what `top_k`
   alone can't do.
3. **Return nothing when nothing is relevant** (the negative-control / no-leak family).
4. **Model-robust** — survive an embedding-model swap without re-tuning a precise
   separating value.
5. **Cheap + deterministic** — operate on the `SearchHit.score`s we already have; no
   second model call.

## 4. Design space

| policy | drops irrelevant? | model-robust? | can return empty? | notes |
|--------|:-----------------:|:-------------:|:-----------------:|-------|
| absolute threshold (current) | yes | **no** (pinned) | yes | brittle; needs per-model retune |
| pure `top_k` | **no** | n/a | no (always k) | volume cap only |
| **relative / normalized** ("≥ X% of top") | yes | **yes** | **no** (keeps top-1) | self-calibrating; ≡ max-normalize then threshold |
| **gap-based** (Weaviate `autocut`) | yes | **yes** | **no** (keeps first cluster) | parameter-free; degrades on smooth curves |
| quantity-based adaptive | partial | partial | no | relaxes threshold until *N* hits; different axis |

Two observations decide it:

- The **relative** and **gap** policies both satisfy criteria 1, 2, 4 and are the
  documented, production-proven responses to absolute-threshold brittleness (§6). On
  our data both isolate exactly the two relevant facts (relative: 0.8 × 0.516 = 0.413
  cutoff; gap: cut at the 0.45→0.27 jump).
- **Neither can return empty** — a relative cutoff always keeps the top-1 (it's 100% of
  itself), and `autocut` always returns the first cluster. So criterion 3 is *not*
  met by the relative piece alone. It needs an **absolute floor** underneath.

## 5. Recommendation

**`RetrievingReader` cutoff = floor → relative → cap**, three global constants:

```
hits = search(query)                       # cosine similarity, higher = better
hits = [h for h in hits if h.score >= ABS_FLOOR]      # 1. existence: is anything good?
if hits:
    top = hits[0].score
    hits = [h for h in hits if h.score >= REL_RATIO * top]   # 2. shape: keep near-best
hits = hits[:TOP_K]                                   # 3. volume cap
```

- **`ABS_FLOOR`** (~0.30) — "nothing below this is ever relevant." This is the
  negative-control guard: a no-good-match query (top ~0.2) clears nothing → empty
  result → no leak. Coarse and only mildly model-tied (it sits in the unrelated band,
  not on the precise separating line), so far less brittle than today's `0.35`.
- **`REL_RATIO`** (~0.7–0.8) — keep hits within that fraction of the best score. This is
  the model-robust precision knob: it adapts per query and per model.
- **`TOP_K`** (8) — volume backstop.

On the measured data: floor 0.30 drops everything ≤ 0.27 already (so CloudFront/X-Ray/SES
go), and the relative ratio drops anything much weaker than the top. The two relevant
facts survive; the result is the same green as today's `0.35` — but now expressed as a
**model-robust system contract**, not a per-case tuned constant.

**Relative-fraction vs gap (`autocut`) for the middle step** is the one sub-decision
worth calling out (§9 Q1). Fraction is simpler and predictable; gap is parameter-free
and production-proven but degrades when scores are smooth (no clear jump — a documented
`autocut` limitation). I lean **relative-fraction** for a first cut (one obvious knob,
no failure mode on smooth curves), with gap as a later refinement. Either way the floor
and cap stay.

These are **global constants on `RetrievingReader`**, not per-case overrides — per the
"assert the system's actual behavior" principle, the eval then tests the real policy.
The existing `reader_min_score`/`reader_top_k` per-case fields can stay as escape
hatches for exploration but the cases should stop relying on them.

## 6. Prior art

- **Weaviate `autocut`** — production cutoff that "looks for discontinuities, or jumps,
  in result metrics such as vector distance or search score"; the integer says how many
  jumps to allow. The gap-based member of this family.
  ([docs](https://docs.weaviate.io/weaviate/api/graphql/additional-operators),
  [card](https://weaviate.io/learn/knowledgecards/autocut)) Known limitation: ineffective
  when jumps are indistinguishable
  ([forum](https://forum.weaviate.io/t/is-autocut-effective-in-scoring-curves-where-the-jumps-are-indistinguishable/9636)).
- **Absolute thresholds are widely considered brittle** and need careful per-corpus
  tuning, motivating dynamic approaches
  ([RAG score thresholds](https://nickberens.me/blog/understanding-rag-score-thresholds/),
  [similarity-with-threshold](https://meisinlee.medium.com/better-rag-retrieval-similarity-with-threshold-a6dbb535ef9e)).
- **Quantity-based adaptive lowering** — relax the threshold in steps until *N* results
  return ("never come up empty"); a different axis we could layer on later if empties
  become a problem
  ([Adaptive HyDE, arXiv](https://arxiv.org/pdf/2507.16754)).
- **Sign-convention gotcha:** LangChain's `score_threshold` is cosine **distance**, not
  similarity — don't copy a threshold value from those examples. Our
  `VectorGraph.search` returns similarity (higher = better)
  ([LangChain discussion](https://github.com/langchain-ai/langchain/discussions/19227)).

"Keep within X% of the top" ≡ max-normalize the scores then threshold at X — a standard
normalized-thresholding framing.

## 7. Effect on the reader-dependent eval cluster

Deciding this policy reconciles the cases that currently bet on different reader
behaviors (the cluster `reader_returns_all` already names "revisit together"):

| case | today | once this policy lands |
|------|-------|------------------------|
| `lost_in_middle_reader` | provisional, `min_score=0.35`, PASS | **resolves**: re-expressed via the policy (floor+relative still drop CloudFront/X-Ray/SES); drop the `PROVISIONAL` note |
| `lost_in_middle_reader_before` | XFAIL control | unchanged (whole_file control) |
| `reader_returns_all` | PASS (asserts dump-all) | **flips to FAIL** → rewrite/retire: a ranking reader no longer returns the whole graph |
| `scattered_multifact` | PASS (needs all 3 facts) | **at risk**: retrieval may not surface all three for its query → needs a high `top_k`, an explicit whole-file reader, or redesign |
| `context_budget_overload`, `negative_control_irrelevant` | PASS (agent ignores injected junk) | **become floor tests**: retrieval never injects the irrelevant facts (top score < `ABS_FLOOR`) → empty/clean injection; honest no-leak |
| `decayed_lesson_ignored_reader` | XFAIL | **orthogonal**: decay is a metadata/recency filter, not a similarity cutoff — unaffected by this proposal |

This is a system decision (the reader's production behavior); the evals then assert that
actual behavior rather than each guessing. It is also a prerequisite for wiring
`RetrievingReader` into the real serve path — though *that* deployment is a separate
decision from defining the policy here.

## 8. Implementation sketch

1. `RetrievingReader.__init__(graph, *, top_k=8, abs_floor=0.30, rel_ratio=0.75)`;
   `read` applies floor → relative → cap (§5). Defaults are the system contract.
2. Remove the per-case `min_score=0.35` from `lost_in_middle_reader`; it now rides the
   reader defaults. Re-confirm PASS from the committed cache; drop its `PROVISIONAL` note.
3. Rewrite/retire `reader_returns_all` (it asserts the now-falsified dump-all behavior).
4. Decide `scattered_multifact`'s fate (high `top_k` / whole-file / redesign).
5. Tests: a stub-embedder reader test asserting floor (no-relevant → empty), relative
   (drop the weak-but-present), and cap; plus the no-empty-leak negative-control path.
6. Calibrate `ABS_FLOOR`/`REL_RATIO` against the committed cache the same way `min_score`
   was, and document the values + model on the reader.

## 9. Open questions

1. **Relative-fraction vs gap (`autocut`) for the middle step.** Recommendation:
   start with fraction (`REL_RATIO`), add gap later if smooth-curve cases want it.
2. **`ABS_FLOOR` value + model-sensitivity.** ~0.30 for `text-embedding-3-small`; it's
   the one remaining model-tied constant (coarse). Recompute on a model change; consider
   whether a normalized floor is even meaningful (probably not — existence is inherently
   absolute).
3. **`scattered_multifact`.** Genuinely conflicts with ranked retrieval. Keep it on an
   explicit whole-file reader (aggregation is a different contract), or raise `top_k`
   enough to always surface its facts?
4. **Does deciding the policy imply deploying the reader?** No — this fixes the contract
   so the evals are honest; wiring `RetrievingReader` into the serve path is a separate
   proposal.
