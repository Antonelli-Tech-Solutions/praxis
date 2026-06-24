"""U4: structural conflict detector + gray-zone value judge (offline)."""

import json

from knowledge.knowledge_graph.knowledge_graph_def import Claim
from knowledge.knowledge_graph.knowledge_graph_variants.vector_graph import VectorGraph
from knowledge.knowledge_graph.write_policy.parent_write_step import WriteStep
from knowledge.knowledge_graph.write_policy.write_policy_def import WriteDecision
from knowledge.knowledge_graph.write_policy.write_step_variants.claim_conflict_detector import (
    ClaimConflictDetector,
    ClaimValueJudge,
)
from knowledge.llm.llm_variants.fake_llm import FakeLlm


class _MappedClaims(WriteStep):
    consumes_candidates = False

    def __init__(self, mapping):
        self._mapping = mapping

    def apply(self, decision: WriteDecision) -> None:
        decision.claims = list(self._mapping.get(decision.text, []))


def _run(mapping, seeds, incoming, judge=None):
    g = VectorGraph(policy=[_MappedClaims(mapping), ClaimConflictDetector(judge=judge)])
    for s in seeds:
        g.write(s, state="active")
    g.write(incoming, state="active")
    return g


def test_year_conflict_flagged_without_llm():
    # AE1: same functional slot, different numeric values -> deterministic conflict.
    mapping = {
        "y1801": [Claim(subject="voltaic pile", attribute="invention year", value="1801", functional=True)],
        "y1799": [Claim(subject="voltaic pile", attribute="invention year", value="1799", functional=True)],
    }
    g = _run(mapping, ["y1801"], "y1799")  # judge=None: numeric path needs no LLM
    assert len(g.contradictions()) == 1


def test_synonym_values_not_flagged_via_judge():
    # AE5: fuzzy values judged synonymous -> no conflict.
    mapping = {
        "first": [Claim(subject="voltaic pile", attribute="type", value="first electric battery", functional=True)],
        "early": [Claim(subject="voltaic pile", attribute="type", value="early electric battery", functional=True)],
    }
    judge = ClaimValueJudge(llm=FakeLlm(default=json.dumps({"incompatible": False})))
    g = _run(mapping, ["first"], "early", judge=judge)
    assert g.contradictions() == []


def test_fuzzy_conflict_flagged_when_judge_says_incompatible():
    mapping = {
        "blue": [Claim(subject="video:visual", attribute="background", value="solid blue", functional=True)],
        "red": [Claim(subject="video:visual", attribute="background", value="solid red", functional=True)],
    }
    judge = ClaimValueJudge(llm=FakeLlm(default=json.dumps({"incompatible": True})))
    g = _run(mapping, ["blue"], "red", judge=judge)
    assert len(g.contradictions()) == 1


def test_fuzzy_values_suppressed_when_no_judge():
    # Precision-first: fuzzy difference + no judge -> suppress.
    mapping = {
        "blue": [Claim(subject="video:visual", attribute="background", value="solid blue", functional=True)],
        "red": [Claim(subject="video:visual", attribute="background", value="solid red", functional=True)],
    }
    g = _run(mapping, ["blue"], "red", judge=None)
    assert g.contradictions() == []


def test_multivalued_attribute_never_conflicts():
    # AE3: discovery is non-functional -> no recall, no flag.
    mapping = {
        "m": [Claim(subject="volta", attribute="discovery", value="methane", functional=False)],
        "s": [Claim(subject="volta", attribute="discovery", value="electrochemical series", functional=False)],
    }
    g = _run(mapping, ["m"], "s")
    assert g.contradictions() == []


def test_distinct_subjects_do_not_conflict():
    # AE2/AE4: same attribute, different subjects -> different slot -> no conflict.
    mapping = {
        "como": [Claim(subject="como professorship", attribute="appointment year", value="1774", functional=True)],
        "pavia": [Claim(subject="pavia professorship", attribute="appointment year", value="1779", functional=True)],
    }
    g = _run(mapping, ["como"], "pavia")
    assert g.contradictions() == []
