"""US3 write-path tests: embed once, one shared recall pass for both judges.

These pin SC-007: a single ``write`` embeds the incoming text exactly once (the
merge judge, the conflict judge, and persistence all share that vector and the
one candidate-recall pass), and a merged duplicate triggers zero conflict checks
(merge runs before conflict; a merge short-circuits it).

Offline via ``FakeEmbedder`` (hash-based, so non-identical texts sit at ~0
cosine). ``recall_floor=-1.0`` opts the candidate into the recall set despite the
fake embedder's low similarity, so the judge wiring is exercised deterministically.
"""

from __future__ import annotations

from knowledge.knowledge_graph.knowledge_graph_variants.vector_graph import VectorGraph
from knowledge.knowledge_graph.write_policy.write_step_variants import (
    ConflictFlagger,
    ConflictJudge,
    Deduper,
    MergeJudge,
)
from knowledge.llm.embedder_variants.fake_embedder import FakeEmbedder
from knowledge.llm.llm_def import Vector
from knowledge.llm.llm_variants.fake_llm import FakeLlm
from knowledge.llm.parent_embedder import Embedder


class _CountingEmbedder(Embedder):
    """Wraps FakeEmbedder, recording every text it embeds (to count re-embeds)."""

    def __init__(self) -> None:
        self._inner = FakeEmbedder()
        self.embedded: list[str] = []

    def embed(self, texts: list[str]) -> list[Vector]:
        self.embedded.extend(texts)
        return self._inner.embed(texts)


def test_single_write_embeds_incoming_text_once():
    # One write into a non-empty graph must embed the incoming text exactly once,
    # shared by the recall pass and persistence (no per-judge or store-time re-embed).
    emb = _CountingEmbedder()
    g = VectorGraph(embedder=emb)
    g.write("first fact about deployment scripts", state="active")
    emb.embedded.clear()
    g.write("second fact about the test command", state="active")
    assert emb.embedded.count("second fact about the test command") == 1


def test_one_recall_pass_feeds_both_judges():
    # A single recall pass (one embed) feeds both the merge judge and the conflict
    # judge: each is consulted exactly once on the same recalled candidate.
    emb = _CountingEmbedder()
    merge_llm = FakeLlm(default='{"same_lesson": false}')  # not a duplicate
    conflict_llm = FakeLlm(default='{"contradicts": false}')  # not a contradiction
    policy = [
        Deduper(judge=MergeJudge(llm=merge_llm)),
        ConflictFlagger(judge=ConflictJudge(llm=conflict_llm)),
    ]
    g = VectorGraph(embedder=emb, policy=policy, recall_floor=-1.0)
    g.write("alpha fact", state="active")
    emb.embedded.clear()
    g.write("beta fact", state="active")
    assert emb.embedded.count("beta fact") == 1  # one embed powers the shared recall
    assert len(merge_llm.calls) == 1  # merge judge saw the candidate
    assert len(conflict_llm.calls) == 1  # conflict judge saw the same candidate


def test_below_floor_candidate_is_not_judged():
    # The store's single recall gate filters a below-floor candidate out before the
    # judge — the merge judge is never consulted (FakeEmbedder pairs sit ~0 cosine,
    # below the default recall_floor of 0.45).
    merge_llm = FakeLlm(default='{"same_lesson": true}')
    g = VectorGraph(policy=[Deduper(judge=MergeJudge(llm=merge_llm))])
    g.write("alpha unrelated fact", state="active")
    g.write("beta unrelated fact", state="active")
    assert len(g._facts) == 2  # not merged
    assert merge_llm.calls == []  # below the recall floor -> judge never consulted


def test_merged_dup_triggers_zero_conflict_checks():
    # Merge runs before conflict: when the merge judge collapses the write into an
    # existing fact (action == "update"), the conflict judge is never consulted.
    merge_llm = FakeLlm(default='{"same_lesson": true}')
    conflict_llm = FakeLlm(default='{"contradicts": true}')
    policy = [
        Deduper(judge=MergeJudge(llm=merge_llm)),
        ConflictFlagger(judge=ConflictJudge(llm=conflict_llm)),
    ]
    g = VectorGraph(policy=policy, recall_floor=-1.0)
    g.write("use uv run pytest", state="active")
    g.write("run the suite with uv run pytest", state="active")  # paraphrase -> merge
    assert any(f.observation_count == 2 for f in g._facts)  # merged into the survivor
    assert conflict_llm.calls == []  # conflict judge skipped on a merge
