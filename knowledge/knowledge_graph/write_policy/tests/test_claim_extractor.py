"""U2: claim extraction write step + cassette (offline via FakeLlm)."""

import json

from knowledge.knowledge_graph.knowledge_graph_variants.vector_graph import VectorGraph
from knowledge.knowledge_graph.write_policy.write_step_variants.claim_extractor import (
    ClaimExtractionJudge,
    ClaimExtractor,
)
from knowledge.knowledge_graph.write_policy.write_step_variants.redactor import Redactor
from knowledge.llm.llm_variants.fake_llm import FakeLlm
from knowledge.llm.verdict_cassette import VerdictCassette

_PAYLOAD = json.dumps(
    {
        "claims": [
            {"subject": "voltaic pile", "attribute": "invention year",
             "value": "1799", "functional": True},
            {"subject": "Volta", "attribute": "discovery",
             "value": "methane", "functional": False},
        ]
    }
)


def test_extractor_populates_claims_with_functional_flag():
    judge = ClaimExtractionJudge(llm=FakeLlm(default=_PAYLOAD))
    g = VectorGraph(policy=[Redactor(), ClaimExtractor(judge=judge)])
    g.write("Volta invented the voltaic pile in 1799; he also discovered methane.", state="active")
    claims = g.facts[0].claims
    assert {(c.attribute, c.functional) for c in claims} == {
        ("invention year", True),
        ("discovery", False),
    }


def test_no_judge_is_inert():
    g = VectorGraph(policy=[Redactor(), ClaimExtractor(judge=None)])
    g.write("some fact", state="active")
    assert g.facts[0].claims == []


def test_no_source_skips_without_error():
    # Judge with neither cassette nor llm returns None -> no claims, no raise.
    judge = ClaimExtractionJudge(llm=None, cassette=None)
    g = VectorGraph(policy=[ClaimExtractor(judge=judge)])
    g.write("some fact", state="active")
    assert g.facts[0].claims == []


def test_malformed_claim_is_dropped_precision_first():
    bad = json.dumps({"claims": [{"subject": "x", "attribute": "y"}]})  # missing value/functional
    judge = ClaimExtractionJudge(llm=FakeLlm(default=bad))
    assert judge.extract("note") == []


def test_cassette_records_then_replays_without_llm(tmp_path):
    path = tmp_path / "claims.json"
    llm = FakeLlm(default=_PAYLOAD)
    rec = VerdictCassette(path, model_id="test-model", allow_compute=True)
    first = ClaimExtractionJudge(llm=llm, cassette=rec).extract("note text")
    # Two LLM calls per extract: free-form claims + the dedicated stance classifier.
    assert len(first) == 2 and len(llm.calls) == 2
    # Replay with no llm and compute disabled: must serve from the cassette.
    replay = VerdictCassette(path, model_id="test-model", allow_compute=False)
    second = ClaimExtractionJudge(llm=None, cassette=replay).extract("note text")
    assert [(c.subject, c.value) for c in second] == [(c.subject, c.value) for c in first]
