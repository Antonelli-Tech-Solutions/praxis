"""Offline U2 tests: map-mutation (skipped without swebench), report parsing, predictions shape.

The live Docker grade is exercised by the scratchpad smoke driver, not here. This layer
covers only the pure pieces: ``prepare`` mutating the in-memory swebench maps (skipped where
swebench isn't installed), ``parse_report`` reading committed sample reports, and
``write_predictions`` shape/LF + empty-patch behavior.

    uv run pytest knowledge/evals/swebench/tests/test_grader.py -q
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from knowledge.evals.swebench.grader import (
    GradeResult,
    grade,
    parse_report,
    prepare,
    write_predictions,
)
from knowledge.evals.swebench.instances import Instance

FIXTURES = Path(__file__).parent / "fixtures"


def _instance() -> Instance:
    records = json.loads((FIXTURES / "rebench_sample.json").read_text(encoding="utf-8"))
    return Instance.from_record(records[0])  # sympy__sympy-fake-0001, version 1.13


# ---- override application (needs swebench; skips on the host) ---------------------------


def test_prepare_applies_test_cmd_and_parser_overrides():
    swebench = pytest.importorskip("swebench")  # noqa: F841 — Docker-host-only dependency
    from swebench.harness import log_parsers as lp
    from swebench.harness import grading
    from swebench.harness.constants import MAP_REPO_VERSION_TO_SPECS

    inst = _instance()
    prepare(inst)

    spec = MAP_REPO_VERSION_TO_SPECS["sympy/sympy"][inst.version]
    assert spec["test_cmd"] == inst.install_config["test_cmd"]

    pytest_parser = lp.MAP_REPO_TO_PARSER["pydata/xarray"]
    assert lp.MAP_REPO_TO_PARSER["sympy/sympy"] is pytest_parser
    assert grading.MAP_REPO_TO_PARSER["sympy/sympy"] is pytest_parser
    assert pytest_parser.__name__ == "parse_log_pytest"


# ---- report.json parsing (pure) ---------------------------------------------------------


def test_parse_report_all_passing_resolved():
    inst = _instance()
    report = json.loads((FIXTURES / "report_resolved.json").read_text(encoding="utf-8"))

    result = parse_report(report, inst)

    assert isinstance(result, GradeResult)
    assert result.resolved is True
    assert result.fail_to_pass == {"sympy/matrices/tests/test_dense.py::test_empty_mul": "PASSED"}
    assert result.pass_to_pass == {"sympy/matrices/tests/test_dense.py::test_basic_mul": "PASSED"}
    assert result.empty_patch is False


def test_parse_report_target_failing_unresolved():
    inst = _instance()
    report = json.loads((FIXTURES / "report_unresolved.json").read_text(encoding="utf-8"))

    result = parse_report(report, inst)

    assert result.resolved is False
    assert result.fail_to_pass["sympy/matrices/tests/test_dense.py::test_empty_mul"] == "FAILED"
    assert result.pass_to_pass["sympy/matrices/tests/test_dense.py::test_basic_mul"] == "PASSED"


# ---- predictions-file shape (pure) ------------------------------------------------------


def test_write_predictions_lf_and_instance_id(tmp_path):
    path = tmp_path / "preds.json"
    write_predictions("sympy__sympy-fake-0001", "diff --git a/x b/x\n+line\n", path)

    raw = path.read_bytes()
    assert b"\r\n" not in raw  # LF endings only

    row = json.loads(raw.decode("utf-8"))
    assert isinstance(row, list) and len(row) == 1
    assert row[0]["instance_id"] == "sympy__sympy-fake-0001"
    assert row[0]["model_patch"] == "diff --git a/x b/x\n+line\n"


def test_grade_empty_patch_unresolved_without_docker(tmp_path):
    inst = _instance()
    pred_path = tmp_path / "preds.json"

    def _fail_if_called(**kwargs):  # the Docker seam must not fire for an empty patch
        raise AssertionError("run_evaluation should not be invoked for an empty patch")

    result = grade(
        inst, "   \n  ", predictions_path=pred_path, run_evaluation=_fail_if_called
    )

    assert result.resolved is False
    assert result.empty_patch is True
    assert pred_path.exists()  # the empty patch still wrote a predictions row
    row = json.loads(pred_path.read_text(encoding="utf-8"))
    assert row[0]["instance_id"] == "sympy__sympy-fake-0001"
