"""Unit tests for the composable write-policy steps."""

from knowledge.knowledge_graph.knowledge_graph_def import Fact, SearchHit
from knowledge.knowledge_graph.write_policy.write_policy_def import WriteDecision
from knowledge.knowledge_graph.write_policy.write_step_variants import (
    ConflictFlagger,
    Deduper,
    Redactor,
)
from knowledge.llm.llm_variants.fake_llm import FakeLlm


class _StoreView:
    """A scripted StoreView: returns the given hits for any query."""

    def __init__(self, hits=None):
        self._hits = hits or []

    def most_similar(self, text, k=5):
        return self._hits[:k]


def test_redactor_scrubs_email_and_keys():
    d = WriteDecision(text="email jane.doe@example.com key sk-live-ABCDEFGH123")
    Redactor().apply(d, _StoreView())
    assert "jane.doe@example.com" not in d.text
    assert "sk-live-ABCDEFGH123" not in d.text
    assert "[REDACTED]" in d.text


def test_deduper_marks_exact_match_as_update():
    existing = Fact(id="f1", text="use uv run pytest", embedding=[1.0, 0.0])
    d = WriteDecision(text="use uv run pytest")
    Deduper().apply(d, _StoreView([SearchHit(fact=existing, score=1.0)]))
    assert d.action == "update"
    assert d.update_target_id == "f1"


def test_deduper_adds_when_no_similar():
    d = WriteDecision(text="brand new fact")
    Deduper().apply(d, _StoreView([]))
    assert d.action == "add"


def test_conflict_flagger_flags_on_llm_yes():
    existing = Fact(id="f9", text="use 2 spaces", embedding=[1.0, 0.0])
    d = WriteDecision(text="use 4 spaces")
    flagger = ConflictFlagger(llm=FakeLlm(default="yes"))
    flagger.apply(d, _StoreView([SearchHit(fact=existing, score=0.9)]))
    assert any(f.startswith("contradiction:f9") for f in d.flags)


def test_conflict_flagger_inert_without_llm():
    existing = Fact(id="f9", text="use 2 spaces", embedding=[1.0, 0.0])
    d = WriteDecision(text="use 4 spaces")
    ConflictFlagger(llm=None).apply(d, _StoreView([SearchHit(fact=existing, score=0.9)]))
    assert d.flags == []
