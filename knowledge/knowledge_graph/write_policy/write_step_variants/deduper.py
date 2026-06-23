"""Deduplicate a candidate against existing facts (exact + semantic).

Two stages, recall then precision:

1. **Exact-match short-circuit** — byte-identical text collapses to an ``update``
   (bump the existing fact). Works with any embedder, no judge needed.
2. **Semantic merge** — a *loose* cosine recall gate (``recall_floor``) surfaces
   paraphrase candidates; a :class:`MergeJudge` (precision) decides whether each
   records the same lesson. No cosine threshold decides the merge — the judge does,
   and it keeps the existing note verbatim.

The recall gate is high-recall by design (forgiving of model drift): its only job is
"don't miss a true dup". With the offline ``FakeEmbedder`` paraphrases score far below
the floor, so offline behavior is exact-dedup only; a real embedder + judge enables
paraphrase merge. With no judge wired, only stage 1 runs (graceful).
"""

from __future__ import annotations

from knowledge.knowledge_graph.write_policy.parent_write_step import WriteStep
from knowledge.knowledge_graph.write_policy.write_policy_def import StoreView, WriteDecision
from knowledge.knowledge_graph.write_policy.write_step_variants.merge_judge import MergeJudge


class Deduper(WriteStep):
    def __init__(
        self, recall_floor: float = 0.45, judge: MergeJudge | None = None, k: int = 5
    ) -> None:
        self.recall_floor = recall_floor
        self.judge = judge
        self.k = k

    def apply(self, decision: WriteDecision, store: StoreView) -> None:
        if decision.dropped:
            return
        hits = store.most_similar(decision.text, k=self.k)
        if not hits:
            return

        # 1. Exact-match short-circuit (any embedder, no judge).
        for hit in hits:
            if hit.fact.text.strip() == decision.text.strip():
                decision.action = "update"
                decision.update_target_id = hit.fact.id
                return

        # 2. Semantic merge: recall gate -> judge. Skipped entirely without a judge.
        if self.judge is None:
            return
        for hit in hits:  # hits are best-first
            if hit.score < self.recall_floor:
                break  # below the recall gate; nothing closer remains
            if self.judge.same_lesson(decision.text, hit.fact.text):
                decision.action = "update"  # merge into the existing verbatim survivor
                decision.update_target_id = hit.fact.id
                return
