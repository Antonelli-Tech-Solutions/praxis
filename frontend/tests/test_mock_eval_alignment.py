"""Assert mock_data.py rows align with P0 eval case registry (MATTHEW_HANDOFF)."""

from __future__ import annotations

from mock_data import get_mock_candidate_dicts

# Mirrors knowledge/evals/cases/MATTHEW_HANDOFF.md case ↔ candidate table.
_P0_EVAL_ALIGNMENT: dict[str, dict[str, object]] = {
    "quirky_exhaustive_switch": {
        "candidate_ids": ["cand_1"],
        "title": "TypeScript Exhaustive Switch Pattern",
        "provenance": "logs/session_20260615.jsonl:88",
    },
    "quirky_config_load_order": {
        "candidate_ids": ["cand_9", "cand_16"],
        "primary_id": "cand_9",
        "rival_id": "cand_16",
        "title": "experimental_options Before Config Load",
        "provenance": "logs/nushell_contrib_20260611.jsonl:56",
        "contradiction_pair": ("cand_9", "cand_16"),
    },
    "pathlib_preference": {
        "candidate_ids": ["cand_18"],
        "title": "Prefer pathlib Over os.path",
        "provenance": "logs/session_20260616.jsonl:201",
    },
    "poison_negative_control_good": {
        "candidate_ids": ["cand_19"],
        "title": "Docstring and Test Policy Before Merge",
        "provenance": "logs/session_poison_demo.jsonl:14",
    },
    "poison_negative_control_bad": {
        "candidate_ids": ["cand_20"],
        "title": "Never Add Docstrings",
        "provenance": "logs/session_poison_demo.jsonl:22",
        "rival_of": "cand_19",
    },
}


def _rows_by_id() -> dict[str, dict]:
    return {row["id"]: row for row in get_mock_candidate_dicts()}


def test_p0_eval_case_ids_present_on_mock_rows() -> None:
    rows = _rows_by_id()
    for case_id, spec in _P0_EVAL_ALIGNMENT.items():
        for candidate_id in spec["candidate_ids"]:
            row = rows[candidate_id]
            assert row.get("evalCaseId") == case_id, f"{candidate_id} evalCaseId"


def test_p0_eval_titles_and_provenance() -> None:
    rows = _rows_by_id()
    for case_id, spec in _P0_EVAL_ALIGNMENT.items():
        primary_id = str(spec["candidate_ids"][0])
        row = rows[primary_id]
        assert row["title"] == spec["title"], case_id
        assert row["provenance"] == spec["provenance"], case_id


def test_quirky_config_load_order_contradiction_pair() -> None:
    rows = _rows_by_id()
    cand_9 = rows["cand_9"]
    cand_16 = rows["cand_16"]
    assert "cand_16" in cand_9.get("contradiction_ids", [])
    assert "cand_9" in cand_16.get("contradiction_ids", [])
    assert cand_16.get("evalCaseRole") == "rival"


def test_poison_control_contradiction_pair() -> None:
    rows = _rows_by_id()
    cand_19 = rows["cand_19"]
    cand_20 = rows["cand_20"]
    assert "cand_20" in cand_19.get("contradiction_ids", [])
    assert "cand_19" in cand_20.get("contradiction_ids", [])
    assert cand_20.get("evalCaseRole") == "rival"
