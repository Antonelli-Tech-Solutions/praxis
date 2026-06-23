"""Tests for the MergeJudge (same-lesson decision, cassette replay, graceful skip).

The judge uses structured output, so the FakeLlm returns a JSON object
``{"same_lesson": ...}`` (what the real model is constrained to emit).
"""

from knowledge.knowledge_graph.write_policy.write_step_variants.merge_judge import (
    MergeJudge,
)
from knowledge.llm.llm_variants.fake_llm import FakeLlm
from knowledge.llm.verdict_cassette import VerdictCassette

_YES = '{"same_lesson": true}'
_NO = '{"same_lesson": false}'


def test_same_lesson_true_on_structured_yes():
    judge = MergeJudge(llm=FakeLlm(default=_YES))
    assert judge.same_lesson("use uv run pytest", "run the suite with uv run pytest") is True


def test_same_lesson_false_on_structured_no():
    judge = MergeJudge(llm=FakeLlm(default=_NO))
    assert judge.same_lesson("use uv run pytest", "the API is versioned under /v1") is False


def test_skips_when_no_llm_and_no_cassette():
    assert MergeJudge().same_lesson("a", "b") is None  # nothing to decide with -> skip


def test_replays_from_cassette_without_llm(tmp_path):
    path = tmp_path / "merge.json"
    rec = MergeJudge(
        llm=FakeLlm(default=_YES),
        cassette=VerdictCassette(path, model_id="m", allow_compute=True),
    )
    assert rec.same_lesson("incoming", "existing") is True
    # Replay offline: no llm, replay-only cassette -> still resolves.
    replay = MergeJudge(cassette=VerdictCassette(path, model_id="m", allow_compute=False))
    assert replay.same_lesson("incoming", "existing") is True


def test_requests_structured_output_with_verbatim_existing_text():
    # The judge selects (it never rewrites): the prompt carries the existing text
    # verbatim, and the call requests the structured schema.
    llm = FakeLlm(default=_YES)
    judge = MergeJudge(llm=llm)
    assert judge.same_lesson("new wording", "ORIGINAL VERBATIM") is True
    assert "ORIGINAL VERBATIM" in llm.calls[0][0].content
