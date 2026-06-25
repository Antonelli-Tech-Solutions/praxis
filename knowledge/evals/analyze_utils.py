"""Shared trial-loop primitives for the PR-knowledge experiment analyzers.

Both the dogfood suite (cost-to-correct gate) and the auto-distill suite
(token/turn delta + footgun-flip gate with 3-way attribution) run the same real
``ClaudeCodeRunner`` in-process and parse the same transcript usage. The *gate
logic* differs and stays in each suite's ``analyze.py``; this module holds only the
common core — usage extraction, stats, deterministic-check evaluation, and the
per-arm ``measure`` primitive — so it is not built or maintained twice.

Run-by-path repo bootstrap stays inline in each suite's ``analyze.py`` (it must run
*before* any ``knowledge`` import, so it can't live behind this import).
"""

from __future__ import annotations

import statistics

from knowledge.evals.claude_code import _claude_usage

# A footgun "flips" only if the control reliably EXHIBITS it (a control that dodges
# the footgun blind proves nothing). The validity bar is ~2/3 — "majority" at n=3,
# honest at n>=4.
EXHIBIT_BAR = 2 / 3


# --- transcript usage extraction ------------------------------------------- #

def usage(ctx) -> dict:
    return _claude_usage(getattr(ctx, "raw_response", None) or "")


def cost(ctx) -> float | None:
    return usage(ctx).get("cost_usd")


def turns(ctx) -> int | None:
    return usage(ctx).get("num_turns")


def tokens(ctx) -> int | None:
    u = usage(ctx)
    i, o = u.get("input_tokens"), u.get("output_tokens")
    return None if i is None and o is None else (i or 0) + (o or 0)


# --- stats ------------------------------------------------------------------ #

def mean_sd(values: list[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    return statistics.fmean(values), (statistics.stdev(values) if len(values) > 1 else 0.0)


def rate(flags: list[bool | None]) -> float | None:
    """Fraction of non-None flags that are truthy; None when nothing is determinate."""
    present = [bool(f) for f in flags if f is not None]
    return (sum(present) / len(present)) if present else None


# --- deterministic-check evaluation on a run context ----------------------- #

def check_passes(ctx, correct_check) -> bool | None:
    """Run a ``(ref_str, params)`` deterministic check against ``ctx``; None if no check."""
    if correct_check is None:
        return None
    from knowledge.evals.eval_def import DeterministicCheckRef
    from knowledge.evals.run import resolve_check

    ref_str, params = correct_check
    ref = DeterministicCheckRef(name="correct", ref=ref_str, params=params)
    return resolve_check(ref)(ctx, **ref.params).passed


def measure(ctx, correct_check) -> dict:
    """The per-arm measurement: cost/turns/tokens + the correctness verdict."""
    return {
        "cost": cost(ctx),
        "turns": turns(ctx),
        "tokens": tokens(ctx),
        "correct": check_passes(ctx, correct_check),
    }


# --- reporting -------------------------------------------------------------- #

def fmt(v, money: bool = False) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, bool):
        return str(v)
    return f"${v:.4f}" if money else (f"{v:.2f}" if isinstance(v, float) else str(v))
