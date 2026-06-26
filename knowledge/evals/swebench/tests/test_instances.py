"""Offline U1 tests: selection, version filter, leakage screen, gold-file parse, manifest.

Runs fully offline — fixture records go straight to ``load_candidates``; the HF
``datasets`` seam (:func:`fetch_rebench_sympy`) is never touched.

    uv run pytest knowledge/evals/swebench/tests/test_instances.py -q
"""

from __future__ import annotations

import json
from pathlib import Path

from knowledge.evals.swebench.instances import (
    Instance,
    gold_files,
    load_candidates,
    read_manifest,
    screen_leakage,
    select,
    version_supported,
    write_manifest,
)

FIXTURE = Path(__file__).parent / "fixtures" / "rebench_sample.json"


def _records() -> list[dict]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _by_id(instances: list[Instance]) -> dict[str, Instance]:
    return {i.instance_id: i for i in instances}


def test_version_filter_excludes_unsupported_version():
    candidates = load_candidates(_records())
    chosen = select(candidates, n=10)
    ids = {i.instance_id for i in chosen}
    # 1.9 record (fake-0004-oldver) is outside MAP_REPO_VERSION_TO_SPECS coverage → dropped.
    assert "sympy__sympy-fake-0004-oldver" not in ids
    assert all(version_supported(i.version) for i in chosen)
    assert version_supported("1.13") and not version_supported("1.9")


def test_leakage_screen_flags_symbol_overlap_passes_clean():
    by_id = _by_id(load_candidates(_records()))

    leaky = by_id["sympy__sympy-fake-0002-leaky"]
    flag, reason = screen_leakage(leaky)
    assert flag is True
    assert "simplify_radical_quotient" in reason

    clean = by_id["sympy__sympy-fake-0001"]
    flag, reason = screen_leakage(clean)
    assert flag is False
    assert reason == "no problem_statement / gold overlap"


def test_screening_records_a_verdict_for_every_chosen_instance():
    # R2: no silent inclusion — every kept instance carries a recorded verdict, and a
    # flagged instance is kept (not dropped), just marked.
    chosen = select(load_candidates(_records()), n=10)
    assert chosen, "expected at least one supported instance"
    for inst in chosen:
        assert isinstance(inst.leak_flag, bool)
        assert inst.screen_reason  # non-empty reason recorded for every instance
    assert any(i.leak_flag for i in chosen), "the leaky fixture record should remain, marked"


def test_selection_is_deterministic_and_sorted_desc_by_created_at():
    chosen = select(load_candidates(_records()), n=10)
    dates = [i.created_at for i in chosen]
    assert dates == sorted(dates, reverse=True)
    # Newest supported record first; stable across repeated calls.
    assert chosen[0].instance_id == "sympy__sympy-fake-0003"
    again = select(load_candidates(_records()), n=10)
    assert [i.instance_id for i in again] == [i.instance_id for i in chosen]


def test_gold_files_parsed_from_gold_patch():
    by_id = _by_id(load_candidates(_records()))
    assert by_id["sympy__sympy-fake-0001"].gold_files == ["sympy/matrices/dense.py"]
    assert by_id["sympy__sympy-fake-0003"].gold_files == ["sympy/integrals/integrals.py"]
    # Direct parse of a two-file diff preserves order and b/ targets.
    patch = (
        "diff --git a/pkg/x.py b/pkg/x.py\n@@ -1 +1 @@\n-a\n+b\n"
        "diff --git a/pkg/y.py b/pkg/y.py\n@@ -1 +1 @@\n-c\n+d\n"
    )
    assert gold_files(patch) == ["pkg/x.py", "pkg/y.py"]


def test_manifest_round_trips_to_identical_chosen_set(tmp_path):
    chosen = select(load_candidates(_records()), n=10)
    path = tmp_path / "instances.manifest.json"
    write_manifest(chosen, path)
    rows = read_manifest(path)
    assert rows == [i.to_manifest_row() for i in chosen]
    # The lean row carries exactly the committed fields.
    assert set(rows[0]) == {
        "instance_id", "version", "base_commit", "created_at",
        "gold_files", "leak_flag", "screen_reason", "human_reviewed",
    }


def test_from_record_carries_install_config_verbatim():
    rec = _records()[0]
    inst = Instance.from_record(rec)
    assert inst.install_config == rec["install_config"]
    assert inst.fail_to_pass == rec["FAIL_TO_PASS"]
    assert inst.pass_to_pass == rec["PASS_TO_PASS"]
    assert inst.human_reviewed is False
