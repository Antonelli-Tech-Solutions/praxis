"""Offline tests for the real-Claude-Code runner/judge wiring.

The CLI invocation is faked, so these verify the sealed-box flags, subscription
auth (no API key), system-prompt knowledge injection, and output handling
without launching the binary.
"""

import json
from pathlib import Path

from knowledge.evals.claude_code import ClaudeCodeJudge, ClaudeCodeRunner
from knowledge.evals.eval_def import EvalCase, EvalContext, Rubric, RubricItem
from knowledge.wiring import build_trio


def _case():
    return EvalCase.model_validate(
        {
            "id": "iambic_poem",
            "seed_prompt": "Write a poem to poem.txt",
            "target_commit": "abc",
            "deterministic_checks": [{"name": "x", "ref": "m:f"}],
        }
    )


def test_runner_injects_knowledge_boxes_and_scrubs_api_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-should-be-scrubbed")
    captured = {}

    def fake_cli(args, cwd, env, timeout):
        captured["args"] = args
        captured["cwd"] = Path(cwd)
        captured["env"] = env
        # Simulate the agent writing the artifact into the box.
        (Path(cwd) / "poem.txt").write_text("a boxed poem", encoding="utf-8")
        return json.dumps({"result": "done"})

    graph, _, reader = build_trio()  # fresh in-memory graph
    graph.write("Always write in iambic pentameter.")

    ctx = ClaudeCodeRunner(run_cli=fake_cli).run(_case(), reader)

    assert ctx.output == "a boxed poem"
    assert "ANTHROPIC_API_KEY" not in captured["env"]  # subscription auth
    # Knowledge injected via system prompt — no file on disk.
    assert "--append-system-prompt" in captured["args"]
    idx = captured["args"].index("--append-system-prompt")
    assert "iambic pentameter" in captured["args"][idx + 1]
    # Box restrictions present; cwd is a throwaway dir the runner created.
    assert "WebSearch" in captured["args"] and "Bash" in captured["args"]
    assert "bypassPermissions" in captured["args"]
    assert isinstance(captured["cwd"], Path)


def test_runner_omits_injection_when_graph_empty():
    def fake_cli(args, cwd, env, timeout):
        assert "--append-system-prompt" not in args  # nothing to inject
        return json.dumps({"result": "inline poem text"})

    graph, _, reader = build_trio()  # empty graph
    ctx = ClaudeCodeRunner(run_cli=fake_cli).run(_case(), reader)
    assert ctx.output == "inline poem text"  # falls back to result text


def test_judge_parses_overall_score():
    def fake_cli(args, cwd, env, timeout):
        return json.dumps({"result": '{"per_item": {"on_topic": 1.0}, "overall": 0.83}'})

    rubric = Rubric(id="r", items=[RubricItem(id="on_topic", criterion="about the sea")])
    judge = ClaudeCodeJudge(run_cli=fake_cli)
    score = judge(rubric, EvalContext(case_id="c", output="some poem"))
    assert score == 0.83
