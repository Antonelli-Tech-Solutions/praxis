"""Deduplicate a candidate against existing facts.

Exact duplicates collapse to a NOOP (bump the existing fact's observation
count). Semantic near-duplicates (cosine >= ``threshold``) also NOOP — but that
only fires with a real embedder; the deterministic FakeEmbedder gives identical
vectors only for identical text, so offline behavior is exact-dedup.
"""

from __future__ import annotations

from knowledge.knowledge_graph.write_policy.parent_write_step import WriteStep
from knowledge.knowledge_graph.write_policy.write_policy_def import StoreView, WriteDecision


class Deduper(WriteStep):
    def __init__(self, threshold: float = 0.95) -> None:
        self.threshold = threshold

    def apply(self, decision: WriteDecision, store: StoreView) -> None:
        if decision.dropped:
            return
        hits = store.most_similar(decision.text, k=1)
        if not hits:
            return
        top = hits[0]
        is_exact = top.fact.text.strip() == decision.text.strip()
        if is_exact or top.score >= self.threshold:
            decision.action = "update"  # merge into the existing fact, don't add
            decision.update_target_id = top.fact.id
