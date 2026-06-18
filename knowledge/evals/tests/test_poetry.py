"""Tests for the iambic-pentameter deterministic check."""

from knowledge.evals.deterministic_checks.poetry import (
    count_syllables,
    is_iambic_pentameter,
)
from knowledge.evals.eval_def import EvalContext


def _ctx(text: str) -> EvalContext:
    return EvalContext(case_id="c", output=text)


def test_count_syllables_basic():
    # Coarse vowel-group heuristic: single-vowel-cluster words are exact.
    assert count_syllables("sea") == 1
    assert count_syllables("the") == 1
    assert count_syllables("water") == 2
    assert count_syllables("harbor") == 2


def test_pentameter_passes_on_ten_syllable_lines():
    # Ten monosyllabic words per line -> exactly ten syllables under the heuristic.
    poem = "\n".join(
        [
            "the sea is cold and dark and deep and wide",
            "the gulls fly low and call through mist and rain",
            "the tide rolls in and out through night and day",
            "the wind blows hard and salt spray fills the air",
            "the moon casts light on waves of black and gray",
            "the ship sails far from shore through storm and foam",
        ]
    )
    result = is_iambic_pentameter(_ctx(poem), min_lines=6)
    assert result.passed, result.evidence


def test_too_few_lines_fails():
    result = is_iambic_pentameter(_ctx("a single short line here"), min_lines=6)
    assert not result.passed
    assert "lines" in result.evidence


def test_off_meter_fails():
    poem = "\n".join(["sea"] * 6)  # one syllable each, far from ten
    result = is_iambic_pentameter(_ctx(poem), min_lines=6)
    assert not result.passed
    assert "off-meter" in result.evidence
