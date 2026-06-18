"""Deterministic poetry checks — meter detection, no model involved.

Iambic pentameter is, strictly, five iambic feet (ten syllables, alternating
unstressed/stressed). Stress is hard to detect reliably without a pronunciation
dictionary, so the MVP check approximates meter by syllable count: each content
line should land near ten syllables. This is a deliberately coarse proxy — good
enough to tell "the agent wrote in roughly pentameter" from "it ignored the
instruction entirely", which is what the eval needs.
"""

from __future__ import annotations

import re

from knowledge.evals.eval_def import CheckResult, EvalContext

_VOWEL_GROUP = re.compile(r"[aeiouy]+")


def count_syllables(word: str) -> int:
    """Heuristic syllable count for a single word."""
    word = re.sub(r"[^a-z]", "", word.lower())
    if not word:
        return 0
    groups = _VOWEL_GROUP.findall(word)
    count = len(groups)
    # Silent trailing 'e' (but never reduce below one).
    if word.endswith("e") and not word.endswith(("le", "ee", "ie")) and count > 1:
        count -= 1
    return max(count, 1)


def _line_syllables(line: str) -> int:
    return sum(count_syllables(w) for w in line.split())


def is_iambic_pentameter(
    ctx: EvalContext,
    *,
    min_lines: int = 4,
    target_syllables: int = 10,
    tolerance: int = 1,
) -> CheckResult:
    """Pass iff the output reads as (approximately) iambic pentameter.

    Requires at least ``min_lines`` non-empty lines, each within ``tolerance``
    syllables of ``target_syllables``.
    """
    lines = [ln.strip() for ln in ctx.output.splitlines() if ln.strip()]
    counts = [(ln, _line_syllables(ln)) for ln in lines]
    in_range = [
        (ln, n) for ln, n in counts if abs(n - target_syllables) <= tolerance
    ]

    enough_lines = len(lines) >= min_lines
    all_on_meter = bool(counts) and len(in_range) == len(counts)
    passed = enough_lines and all_on_meter

    evidence_lines = ", ".join(f"{n}" for _, n in counts) or "no lines"
    if not enough_lines:
        evidence = f"only {len(lines)} lines (need {min_lines}); syllables/line: {evidence_lines}"
    elif not all_on_meter:
        off = [f"{n}:{ln!r}" for ln, n in counts if abs(n - target_syllables) > tolerance]
        evidence = f"off-meter lines (want ~{target_syllables}): " + "; ".join(off)
    else:
        evidence = f"{len(lines)} lines, syllables/line: {evidence_lines}"

    return CheckResult(name="is_iambic_pentameter", passed=passed, evidence=evidence)
