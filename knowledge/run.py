"""Debugger entrypoint: run every eval case through the real Claude Code engine.

Just run it — no flags, no `-m`. Attach a debugger and set breakpoints in
``run_case`` (knowledge/evals/run.py), the runner/judge
(knowledge/evals/claude_code.py), or the checks; this walks the whole suite.

    uv run python run.py        # via the repo-root shim
    uv run python knowledge/run.py

Set ``PRAXIS_EVAL_REAL=0`` to step through with the offline FakeRunner instead
of spending subscription credit.
"""

from __future__ import annotations

import os
import pathlib
import sys

# Put the repo root on sys.path so a direct `python knowledge/run.py` (not just
# `-m`) can resolve the `knowledge` package. Must precede the package imports
# below; a no-op when run via `-m` or the repo-root run.py shim.
if __package__ in (None, ""):
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from knowledge.evals.claude_code import ClaudeCodeJudge, ClaudeCodeRunner
from knowledge.evals.run import FakeRunner, load_cases, run_case, write_baseline
from knowledge.graph_reader.grapher_reader_variants.whole_file_reader import (
    as_claude_tool,
)
from knowledge.wiring import build_trio

# Real Claude Code by default; PRAXIS_EVAL_REAL=0 swaps in the offline FakeRunner.
USE_REAL_CLAUDE_CODE = os.getenv("PRAXIS_EVAL_REAL", "1") != "0"


def demo() -> None:
    """Quick ingest -> store -> read smoke check (no agent involved)."""
    _, ingestor, reader = build_trio()  # fresh in-memory graph
    ingestor.ingest("Prefer pathlib over os.path for new code.")
    ingestor.ingest("The test suite runs with `uv run pytest`.")
    print("=== read_knowledge() ===")
    print(as_claude_tool(reader)["func"]())


def main() -> int:
    """Run every registered eval case end-to-end and write the baseline."""
    if USE_REAL_CLAUDE_CODE:
        runner, judge = ClaudeCodeRunner(), ClaudeCodeJudge()
        print("running all cases through real Claude Code (subscription)...")
    else:
        runner, judge = FakeRunner(), None
        print("running all cases through FakeRunner (offline)...")

    cases = load_cases()
    if not cases:
        print("no cases registered")
        return 0

    results = []
    for case in cases:
        result = run_case(case, runner, judge=judge)
        results.append(result)
        verdict = "PASS" if result.passed else "FAIL"
        score = "" if result.rubric_score is None else f"  rubric={result.rubric_score:.2f}"
        checks = f"{sum(c.passed for c in result.checks)}/{len(result.checks)}"
        print(f"[{verdict}] {result.case_id}  checks={checks}{score}")

    write_baseline(results)
    print(f"\nwrote {len(results)} rows")
    return 0


if __name__ == "__main__":
    main()
