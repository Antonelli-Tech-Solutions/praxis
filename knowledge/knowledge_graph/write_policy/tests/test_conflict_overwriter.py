"""Unit tests for the ConflictOverwriter write step.

Drives the step directly with a scripted candidate set (the store's recall pass):
an LLM "yes" turns the decision into an ``overwrite`` targeting the conflicting
fact; a "no" leaves it a plain ``add``. No network, no DB.
"""

from __future__ import annotations

from knowledge.knowledge_graph.knowledge_graph_def import Fact, SearchHit
from knowledge.knowledge_graph.write_policy.write_policy_def import WriteDecision
from knowledge.knowledge_graph.write_policy.write_step_variants import ConflictOverwriter
from knowledge.llm.llm_variants.fake_llm import FakeLlm


def _decision(text: str, candidate: Fact | None = None) -> WriteDecision:
    d = WriteDecision(text=text)
    if candidate is not None:
        d.candidates = [SearchHit(fact=candidate, score=0.9)]
    return d


def _existing() -> Fact:
    return Fact(id="f1", text="use uv, not pip, in this repo")


def test_yes_overwrites_nearest():
    step = ConflictOverwriter(llm=FakeLlm(default="yes"))
    decision = _decision("use pip, not uv, in this repo", _existing())
    step.apply(decision)
    assert decision.action == "overwrite"
    assert decision.update_target_id == "f1"
    assert decision.supersede_ids == []


def test_no_stays_add():
    step = ConflictOverwriter(llm=FakeLlm(default="no"))
    decision = _decision("use pip, not uv, in this repo", _existing())
    step.apply(decision)
    assert decision.action == "add"
    assert decision.update_target_id is None


def test_no_llm_is_inert():
    step = ConflictOverwriter(llm=None)
    decision = _decision("anything", _existing())
    step.apply(decision)
    assert decision.action == "add"
