"""Tests for the judge VerdictCassette (replay / record / loud-miss)."""

import json

import pytest

from knowledge.llm.verdict_cassette import VerdictCassette


def test_replays_committed_verdict_without_computing(tmp_path):
    path = tmp_path / "merge.json"
    cas = VerdictCassette(path, model_id="m", allow_compute=False)
    # Seed a verdict by recording it once with compute allowed.
    rec = VerdictCassette(path, model_id="m", allow_compute=True)
    rec.verdict("A||B", lambda: {"same_lesson": True})
    # A fresh replay-only cassette returns it without calling compute.
    cas = VerdictCassette(path, model_id="m", allow_compute=False)
    def boom():
        raise AssertionError("compute must not run on a hit")

    assert cas.verdict("A||B", boom) == {"same_lesson": True}


def test_records_on_miss_when_allowed(tmp_path):
    path = tmp_path / "merge.json"
    cas = VerdictCassette(path, model_id="m", allow_compute=True)
    calls = {"n": 0}

    def compute():
        calls["n"] += 1
        return {"same_lesson": False}

    assert cas.verdict("X||Y", compute) == {"same_lesson": False}
    assert calls["n"] == 1
    # Persisted: a new replay-only cassette serves it without recomputing.
    again = VerdictCassette(path, model_id="m", allow_compute=False)
    assert again.verdict("X||Y", compute) == {"same_lesson": False}
    assert calls["n"] == 1  # not recomputed


def test_loud_miss_when_recording_disabled(tmp_path):
    cas = VerdictCassette(tmp_path / "merge.json", model_id="m", allow_compute=False)
    with pytest.raises(RuntimeError, match="cassette miss"):
        cas.verdict("missing", lambda: {"same_lesson": True})


def test_model_id_is_part_of_the_key(tmp_path):
    path = tmp_path / "merge.json"
    VerdictCassette(path, model_id="m1", allow_compute=True).verdict(
        "A||B", lambda: {"same_lesson": True}
    )
    # A different judge model is a clean miss, not a stale hit.
    other = VerdictCassette(path, model_id="m2", allow_compute=False)
    with pytest.raises(RuntimeError, match="cassette miss"):
        other.verdict("A||B", lambda: {"same_lesson": False})


def test_save_merges_concurrent_on_disk_writes(tmp_path):
    path = tmp_path / "merge.json"
    a = VerdictCassette(path, model_id="m", allow_compute=True)
    b = VerdictCassette(path, model_id="m", allow_compute=True)
    a.verdict("pair-a", lambda: {"same_lesson": True})
    b.verdict("pair-b", lambda: {"same_lesson": False})  # b loaded before a's write
    # b's save must merge a's key rather than clobber it.
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert len(on_disk) == 2
