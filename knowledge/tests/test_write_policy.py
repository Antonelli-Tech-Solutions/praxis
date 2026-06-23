"""Unit tests for the composable write-policy steps.

Steps read the store's shared recall pass from ``decision.candidates`` (the store
fills it before the steps run); these tests script that set directly.
"""

from knowledge.knowledge_graph.knowledge_graph_def import Fact, SearchHit
from knowledge.knowledge_graph.write_policy.write_policy_def import WriteDecision
from knowledge.knowledge_graph.write_policy.write_step_variants import (
    Deduper,
    MergeJudge,
    Redactor,
)
from knowledge.llm.llm_variants.fake_llm import FakeLlm


def _decision(text: str, candidates=None) -> WriteDecision:
    d = WriteDecision(text=text)
    d.candidates = candidates or []
    return d


def test_redactor_scrubs_email_and_keys():
    d = WriteDecision(text="email jane.doe@example.com key sk-live-ABCDEFGH123")
    Redactor().apply(d)
    assert "jane.doe@example.com" not in d.text
    assert "sk-live-ABCDEFGH123" not in d.text
    assert "[REDACTED]" in d.text


def test_deduper_marks_exact_match_as_update():
    existing = Fact(id="f1", text="use uv run pytest", embedding=[1.0, 0.0])
    d = _decision("use uv run pytest", [SearchHit(fact=existing, score=1.0)])
    Deduper().apply(d)
    assert d.action == "update"
    assert d.update_target_id == "f1"


def test_deduper_adds_when_no_similar():
    d = _decision("brand new fact", [])
    Deduper().apply(d)
    assert d.action == "add"


def test_deduper_semantic_merge_when_judge_says_same_lesson():
    # Paraphrase recalled by the store; judge says same lesson -> merge into existing.
    existing = Fact(id="f1", text="run the suite with uv run pytest", embedding=[1.0])
    d = _decision("use uv run pytest before pushing", [SearchHit(fact=existing, score=0.67)])
    judge = MergeJudge(llm=FakeLlm(default='{"same_lesson": true}'))
    Deduper(judge=judge).apply(d)
    assert d.action == "update"
    assert d.update_target_id == "f1"  # verbatim survivor is the existing fact


def test_deduper_keeps_both_when_judge_says_distinct():
    existing = Fact(id="f1", text="the API is versioned under /v1", embedding=[1.0])
    d = _decision("use uv run pytest before pushing", [SearchHit(fact=existing, score=0.67)])
    judge = MergeJudge(llm=FakeLlm(default='{"same_lesson": false}'))
    Deduper(judge=judge).apply(d)
    assert d.action == "add"  # judge rejected -> no over-merge


def test_deduper_without_judge_does_exact_only():
    # No judge wired: a recalled paraphrase (non-exact) is NOT merged.
    existing = Fact(id="f1", text="run the suite with uv run pytest", embedding=[1.0])
    d = _decision("use uv run pytest before pushing", [SearchHit(fact=existing, score=0.67)])
    Deduper().apply(d)
    assert d.action == "add"
