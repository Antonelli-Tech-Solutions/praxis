"""Tests for the MergeJudge (same-lesson decision, cassette replay, graceful skip)."""

from knowledge.knowledge_graph.write_policy.write_step_variants.merge_judge import (
    MergeJudge,
)
from knowledge.llm.llm_variants.fake_llm import FakeLlm
from knowledge.llm.verdict_cassette import VerdictCassette


def test_same_lesson_true_on_llm_yes():
    judge = MergeJudge(llm=FakeLlm(default="yes"))
    assert judge.same_lesson("use uv run pytest", "run the suite with uv run pytest") is True


def test_same_lesson_false_on_llm_no():
    judge = MergeJudge(llm=FakeLlm(default="no"))
    assert judge.same_lesson("use uv run pytest", "the API is versioned under /v1") is False


def test_skips_when_no_llm_and_no_cassette():
    assert MergeJudge().same_lesson("a", "b") is None  # nothing to decide with -> skip


def test_replays_from_cassette_without_llm(tmp_path):
    path = tmp_path / "merge.json"
    # Record with a live (fake) judge.
    rec = MergeJudge(
        llm=FakeLlm(default="yes"),
        cassette=VerdictCassette(path, model_id="m", allow_compute=True),
    )
    assert rec.same_lesson("incoming", "existing") is True
    # Replay offline: no llm, replay-only cassette -> still resolves.
    replay = MergeJudge(
        cassette=VerdictCassette(path, model_id="m", allow_compute=False)
    )
    assert replay.same_lesson("incoming", "existing") is True


def test_verbatim_survivor_is_the_existing_note():
    # The judge selects (yes/no); it never returns rewritten text. The caller keeps
    # the EXISTING note verbatim — verified here by the judge taking only texts and
    # returning a bool, with no text mutation surface.
    llm = FakeLlm(default="yes")
    judge = MergeJudge(llm=llm)
    assert judge.same_lesson("new wording", "ORIGINAL VERBATIM") is True
    # the prompt carried the existing text verbatim
    assert "ORIGINAL VERBATIM" in llm.calls[0][0].content
