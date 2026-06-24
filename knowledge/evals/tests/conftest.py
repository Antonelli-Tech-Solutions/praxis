"""Shared offline-judge test helpers.

The judges build their prompt and hand it to an injected seam — the OpenRouter
``post`` or the Claude ``run_cli`` — so a fake that captures the prompt lets a
test assert *prompt construction* (e.g. the REFERENCE block) with no network/CLI.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

# Load the authored control answers by file path: tests/ is not a package (pytest
# rootdir import mode), so a normal dotted import isn't available. The fixtures
# module has no intra-package imports, so exec-by-path is safe. It must be
# registered in sys.modules before exec so its @dataclass can resolve annotations.
_spec = importlib.util.spec_from_file_location(
    "grounding_controls", Path(__file__).parent / "fixtures" / "grounding_controls.py"
)
_grounding_controls = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _grounding_controls
_spec.loader.exec_module(_grounding_controls)


@pytest.fixture
def grounding_controls():
    """The authored grounded/fabricated control pairs (see fixtures/grounding_controls.py)."""
    return _grounding_controls.ALL_CONTROLS


def _chat_response(text: str) -> str:
    """An OpenRouter chat-completions body whose assistant content is ``text``."""
    return json.dumps({"model": "test", "choices": [{"message": {"content": text}}]})


@pytest.fixture
def capture_openrouter_prompt():
    """Return ``(post, seen)``: a fake OpenRouter ``post`` that records the judge
    prompt into ``seen["prompt"]`` and replies with canned per-item scores."""

    def make(scores: dict | None = None):
        seen: dict = {}

        def post(url, payload, headers, timeout):
            seen["prompt"] = payload["messages"][0]["content"]
            return _chat_response(json.dumps({"per_item": scores or {}}))

        return post, seen

    return make


@pytest.fixture
def capture_claude_prompt():
    """Return ``(run_cli, seen)``: a fake Claude ``run_cli`` that records the judge
    prompt (the ``-p`` arg) into ``seen["prompt"]`` and replies with canned scores."""

    def make(scores: dict | None = None):
        seen: dict = {}

        def run_cli(args, cwd, env, timeout):
            seen["prompt"] = args[args.index("-p") + 1]
            return json.dumps({"structured_output": {"per_item": scores or {}}})

        return run_cli, seen

    return make
