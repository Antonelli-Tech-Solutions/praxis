"""Run the full eval pipeline through real Claude Code. No flags, ever.

    uv run python run.py

Attach a debugger and set breakpoints anywhere in the pipeline — run_case
(knowledge/evals/run.py), the runner/judge (knowledge/evals/claude_code.py), or
the deterministic checks — then just run this file. It walks every registered
eval case end-to-end through the real Claude Code engine on your subscription.
"""

from knowledge.run import main

if __name__ == "__main__":
    main()
