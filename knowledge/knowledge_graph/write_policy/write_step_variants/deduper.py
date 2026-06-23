"""Deduplicate a candidate against existing facts (exact + semantic).

Two stages, recall then precision:

1. **Exact-match short-circuit** — byte-identical text collapses to an ``update``
   (bump the existing fact). Works with any embedder, no judge needed.
2. **Semantic merge** — a :class:`MergeJudge` (precision) decides whether each
   recalled candidate records the same lesson. No cosine threshold decides the
   merge — the judge does, and it keeps the existing note verbatim.

Recall is the store's job: it runs one candidate pass per write (a *loose*,
high-recall ``recall_floor``) and hands the result over on
``decision.candidates``. The Deduper reads that shared set — its only job here is
"don't miss a true dup". With the offline ``FakeEmbedder`` paraphrases score far
below the floor, so offline behavior is exact-dedup only; a real embedder + judge
enables paraphrase merge. With no judge wired, only stage 1 runs (graceful).
"""

from __future__ import annotations

from knowledge.knowledge_graph.write_policy.parent_write_step import WriteStep
from knowledge.knowledge_graph.write_policy.write_policy_def import WriteDecision
from knowledge.knowledge_graph.write_policy.write_step_variants.merge_judge import MergeJudge


class Deduper(WriteStep):
    consumes_candidates = True

    def __init__(self, judge: MergeJudge | None = None) -> None:
        self.judge = judge

    def apply(self, decision: WriteDecision) -> None:
        if decision.dropped:
            return
        candidates = decision.candidates  # shared recall pass, best-first, above the floor
        if not candidates:
            return

        # 1. Exact-match short-circuit (any embedder, no judge).
        for hit in candidates:
            if hit.fact.text.strip() == decision.text.strip():
                decision.action = "update"
                decision.update_target_id = hit.fact.id
                return

        # 2. Semantic merge: judge each candidate. Skipped entirely without a judge.
        if self.judge is None:
            return
        for hit in candidates:
            if self.judge.same_lesson(decision.text, hit.fact.text):
                decision.action = "update"  # merge into the existing verbatim survivor
                decision.update_target_id = hit.fact.id
                return
