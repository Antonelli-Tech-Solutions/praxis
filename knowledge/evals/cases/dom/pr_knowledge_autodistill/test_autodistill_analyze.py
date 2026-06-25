"""U5: offline tests for the auto-distill aggregator + R7 attribution (no agent).

The suite's ``analyze.py`` is loaded via importlib under a UNIQUE module name (not a
bare ``import analyze``) and this file has a UNIQUE basename, so it never collides
with the sibling dogfood suite's ``analyze.py`` / ``test_analyze.py`` under pytest's
prepend import mode.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("autodistill_analyze", HERE / "analyze.py")
analyze = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(analyze)

# Minimal task cfgs so aggregate() iterates only the task under test (it reads
# kind + gating; the live-only fields are irrelevant offline).
GATING = {"yoyo": {"kind": "footgun", "gating": True}}


def _arm(cost, turns, tokens, correct=None):
    return {"cost": cost, "turns": turns, "tokens": tokens, "correct": correct}


def _rec(task, kind, auto, control, curated=None):
    return {"task": task, "kind": kind, "auto": auto, "control": control, "curated": curated}


# --- aggregation -----------------------------------------------------------

def test_per_arm_means_and_token_turn_delta():
    # Happy path: per-arm token/turn means + delta direction.
    recs = [_rec("yoyo", "footgun", _arm(0.04, 4, 1000, True), _arm(0.05, 6, 1500, False))
            for _ in range(3)]
    t = analyze.aggregate(recs, tasks=GATING)["tasks"]["yoyo"]

    assert t["auto"]["tokens_mean"] == 1000 and t["control"]["tokens_mean"] == 1500
    assert t["token_delta"] == -500 and t["token_reduced"] is True
    assert t["auto"]["turns_mean"] == 4 and t["control"]["turns_mean"] == 6
    assert t["turn_delta"] == -2 and t["turn_reduced"] is True


def test_footgun_flip_when_control_exhibits_and_auto_avoids():
    avoids = [_rec("yoyo", "footgun", _arm(0.04, 4, 900, True), _arm(0.05, 6, 1500, False))
              for _ in range(3)]
    assert analyze.aggregate(avoids, tasks=GATING)["tasks"]["yoyo"]["flip"] is True

    # Control that does NOT exhibit (avoids blind) -> no flip, even if auto avoids.
    clean = [_rec("yoyo", "footgun", _arm(0.04, 4, 900, True), _arm(0.05, 6, 1500, True))
             for _ in range(3)]
    assert analyze.aggregate(clean, tasks=GATING)["tasks"]["yoyo"]["flip"] is False


def test_curated_flip_tracked_for_gating_task():
    # auto misses, control exhibits, curated (force-injected ideal) avoids.
    recs = [_rec("yoyo", "footgun", _arm(0.04, 4, 1000, False), _arm(0.05, 6, 1500, False),
                 _arm(0.04, 4, 900, True)) for _ in range(3)]
    t = analyze.aggregate(recs, tasks=GATING)["tasks"]["yoyo"]

    assert t["flip"] is False and t["curated_flip"] is True
    # present + surfaced + auto misses + curated flips -> EXTRACTION-QUALITY
    assert analyze.attribute_shortfall(
        flip=t["flip"], fact_in_artifact=True, surfaced=True, curated_flip=t["curated_flip"]
    ) == "EXTRACTION-QUALITY"


def test_missing_arm_token_data_is_error_not_silent_average():
    recs = [_rec("yoyo", "footgun", _arm(None, None, None, True), _arm(0.05, 6, 1500, False))]
    report = analyze.aggregate(recs, tasks=GATING)

    assert "yoyo" not in report["tasks"]
    assert any("missing token data" in e for e in report["errors"])
    assert analyze.evaluate_gate(report)["verdict"] == "NO-GO"


def test_variance_reported_as_spread():
    recs = [
        _rec("yoyo", "footgun", _arm(0.02, 4, 500, True), _arm(0.05, 6, 1500, False)),
        _rec("yoyo", "footgun", _arm(0.10, 4, 2500, True), _arm(0.05, 6, 1500, False)),
    ]
    t = analyze.aggregate(recs, tasks=GATING)["tasks"]["yoyo"]
    assert t["trials"] == 2
    assert t["auto"]["tokens_sd"] and t["auto"]["tokens_sd"] > 0


# --- gate ------------------------------------------------------------------

def test_gate_go_is_always_provisional():
    recs = [_rec("yoyo", "footgun", _arm(0.04, 4, 1000, True), _arm(0.05, 6, 1500, False))
            for _ in range(3)]
    gate = analyze.evaluate_gate(analyze.aggregate(recs, tasks=GATING))

    assert gate["verdict"] == "GO (provisional)"
    assert gate["provisional"] is True and gate["gating_flip"] is True
    assert any("PROVISIONAL" in r for r in gate["reasons"])


def test_gate_nogo_when_gating_footgun_does_not_flip():
    # Auto misses the footgun -> no flip -> NO-GO.
    recs = [_rec("yoyo", "footgun", _arm(0.04, 4, 1000, False), _arm(0.05, 6, 1500, False))
            for _ in range(3)]
    gate = analyze.evaluate_gate(analyze.aggregate(recs, tasks=GATING))

    assert gate["verdict"] == "NO-GO"
    assert gate["gating_flip"] is False
    assert any("did not flip" in r for r in gate["reasons"])


# --- R7 attribution (pure) -------------------------------------------------

def test_attribution_extraction_when_fact_absent_from_artifact():
    assert analyze.attribute_shortfall(
        flip=False, fact_in_artifact=False, surfaced=False, curated_flip=None
    ) == "EXTRACTION"


def test_attribution_retrieval_when_present_but_not_surfaced():
    assert analyze.attribute_shortfall(
        flip=False, fact_in_artifact=True, surfaced=False, curated_flip=True
    ) == "RETRIEVAL"


def test_attribution_knowledge_value_when_present_surfaced_and_curated_also_misses():
    assert analyze.attribute_shortfall(
        flip=False, fact_in_artifact=True, surfaced=True, curated_flip=False
    ) == "KNOWLEDGE-VALUE"


def test_attribution_none_when_auto_arm_flipped():
    assert analyze.attribute_shortfall(
        flip=True, fact_in_artifact=True, surfaced=True, curated_flip=False
    ) is None


def test_attribution_knowledge_value_when_no_curated_arm_to_consult():
    # present + surfaced + auto misses + no curated arm -> default to the weaker-bet read
    assert analyze.attribute_shortfall(
        flip=False, fact_in_artifact=True, surfaced=True, curated_flip=None
    ) == "KNOWLEDGE-VALUE"


# --- gate edge cases -------------------------------------------------------

def test_aggregate_reports_no_trials_as_error():
    report = analyze.aggregate([], tasks=GATING)
    assert "yoyo" not in report["tasks"]
    assert any("no trials" in e for e in report["errors"])
    assert analyze.evaluate_gate(report)["verdict"] == "NO-GO"


def test_gate_nogo_when_gating_task_underpowered():
    # A clean flip on a SINGLE trial must not earn a GO (below MIN_GATING_TRIALS).
    one = [_rec("yoyo", "footgun", _arm(0.04, 4, 1000, True), _arm(0.05, 6, 1500, False))]
    gate = analyze.evaluate_gate(analyze.aggregate(one, tasks=GATING))
    assert gate["verdict"] == "NO-GO"
    assert gate["gating_flip"] is True  # the flip is there...
    assert any("insufficient data" in r for r in gate["reasons"])  # ...but n is too small


def test_gate_no_gating_task_present():
    recs = [_rec("u", "footgun", _arm(0.04, 4, 1000, True), _arm(0.05, 6, 1500, False))
            for _ in range(3)]
    gate = analyze.evaluate_gate(analyze.aggregate(recs, tasks={"u": {"kind": "footgun", "gating": False}}))
    assert gate["verdict"] == "NO-GO"
    assert any("no gating footgun task present" in r for r in gate["reasons"])


# --- R7 presence diagnostics (pure) ----------------------------------------

def test_neutralizing_fact_present_matches_all_marker_terms():
    insights = [{"raw_text": "yoyo migrations must import the knowledge package lazily inside the step."}]
    assert analyze.neutralizing_fact_present(insights, ["lazil", "knowledge"]) is True
    assert analyze.neutralizing_fact_present(insights, ["n_neighbors"]) is False


def test_fact_surfaced_checks_reader_injected_text():
    assert analyze.fact_surfaced("... import KNOWLEDGE lazily inside ...", ["lazil", "knowledge"]) is True
    assert analyze.fact_surfaced("unrelated context dump", ["lazil", "knowledge"]) is False
    assert analyze.fact_surfaced("", ["lazil"]) is False
