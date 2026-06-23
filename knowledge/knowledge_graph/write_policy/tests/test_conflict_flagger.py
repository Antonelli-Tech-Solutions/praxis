"""Tests for the structured ConflictFlagger + ConflictJudge (P3).

Mirrors test_merge_judge: the judge uses structured output, so the FakeLlm
returns a JSON object ``{"contradicts": ...}`` (what the real model is
constrained to emit). The cassette stores only the method-agnostic
``{"contradicts": bool}``; the flagger resolves the contradiction target to the
candidate's runtime id at call time (never stored in the cassette).
"""

import pytest

from knowledge.knowledge_graph.knowledge_graph_def import Fact, SearchHit
from knowledge.knowledge_graph.write_policy.write_policy_def import WriteDecision
from knowledge.knowledge_graph.write_policy.write_step_variants import ConflictFlagger
from knowledge.knowledge_graph.write_policy.write_step_variants.conflict_judge import (
    ConflictJudge,
)
from knowledge.llm.llm_variants.fake_llm import FakeLlm
from knowledge.llm.verdict_cassette import VerdictCassette

_YES = '{"contradicts": true}'
_NO = '{"contradicts": false}'


def _decision(text: str, candidate: Fact) -> WriteDecision:
    d = WriteDecision(text=text)
    d.candidates = [SearchHit(fact=candidate, score=0.9)]
    return d


def test_contradicts_true_on_structured_yes():
    judge = ConflictJudge(llm=FakeLlm(default=_YES))
    assert judge.contradicts("use 4 spaces", "use 2 spaces") is True


def test_contradicts_false_on_structured_no():
    judge = ConflictJudge(llm=FakeLlm(default=_NO))
    assert judge.contradicts("use uv", "the API is versioned under /v1") is False


def test_skips_when_no_llm_and_no_cassette():
    assert ConflictJudge().contradicts("a", "b") is None  # nothing to decide -> skip


def test_requests_structured_output_with_verbatim_existing_text():
    llm = FakeLlm(default=_YES)
    judge = ConflictJudge(llm=llm)
    assert judge.contradicts("new wording", "ORIGINAL VERBATIM") is True
    assert "ORIGINAL VERBATIM" in llm.calls[0][0].content


def test_flagger_appends_contradiction_with_runtime_id():
    existing = Fact(id="f9", text="use 2 spaces")
    d = _decision("use 4 spaces", existing)
    ConflictFlagger(judge=ConflictJudge(llm=FakeLlm(default=_YES))).apply(d)
    assert "contradiction:f9" in d.flags  # target resolved to the candidate id


def test_flagger_no_flag_on_structured_no():
    existing = Fact(id="f9", text="use 2 spaces")
    d = _decision("use 4 spaces", existing)
    ConflictFlagger(judge=ConflictJudge(llm=FakeLlm(default=_NO))).apply(d)
    assert d.flags == []


def test_flagger_inert_without_judge():
    existing = Fact(id="f9", text="use 2 spaces")
    d = _decision("use 4 spaces", existing)
    ConflictFlagger(judge=None).apply(d)
    assert d.flags == []


def test_flagger_skips_on_merge():
    existing = Fact(id="f9", text="use 2 spaces")
    d = _decision("use 4 spaces", existing)
    d.action = "update"  # Deduper merged it -> conflict check skipped
    llm = FakeLlm(default=_YES)
    ConflictFlagger(judge=ConflictJudge(llm=llm)).apply(d)
    assert d.flags == []
    assert llm.calls == []


def test_flagger_best_effort_when_judge_raises():
    class _BoomLlm:
        def complete(self, messages, **_):
            raise RuntimeError("no API key")

    existing = Fact(id="f9", text="use 2 spaces")
    d = _decision("use 4 spaces", existing)
    ConflictFlagger(judge=ConflictJudge(llm=_BoomLlm())).apply(d)  # must not raise
    assert d.flags == []


def test_replays_from_cassette_without_llm(tmp_path):
    path = tmp_path / "conflict.json"
    rec = ConflictJudge(
        llm=FakeLlm(default=_YES),
        cassette=VerdictCassette(path, model_id="m", allow_compute=True),
    )
    assert rec.contradicts("incoming", "existing") is True
    # Replay offline: no llm, replay-only cassette -> still resolves.
    replay = ConflictJudge(cassette=VerdictCassette(path, model_id="m", allow_compute=False))
    assert replay.contradicts("incoming", "existing") is True


def test_loud_miss_when_replay_only_and_uncached(tmp_path):
    replay = ConflictJudge(
        cassette=VerdictCassette(tmp_path / "conflict.json", model_id="m", allow_compute=False)
    )
    with pytest.raises(RuntimeError):
        replay.contradicts("incoming", "existing")
