"""Record real judge verdicts for the authored grounding controls (T020).

Run once locally with ``OPENROUTER_API_KEY`` set to (re)record the committed
cassette that the deterministic gate (``test_run.py`` / T019) replays offline:

    uv run python -m knowledge.evals.tests.fixtures.record_grounding_controls

It grades each control's grounded and fabricated answer WITH the seeded reference
through the pinned judge model, writing the verdicts to ``CASSETTE_PATH``. The
model is pinned here (not read from env) so the committed fixture is stable.
"""

from __future__ import annotations

from pathlib import Path

from knowledge.evals.eval_def import EvalContext, Rubric, RubricItem
from knowledge.evals.openrouter import OpenRouterClient, OpenRouterJudge
from knowledge.llm.verdict_cassette import VerdictCassette

# Pinned so the committed cassette is reproducible regardless of OPENROUTER_JUDGE_MODEL.
JUDGE_MODEL = "openai/gpt-4.1"
CASSETTE_PATH = Path(__file__).parent / "grounding_controls_verdicts.json"


def _import_controls():
    """Load the sibling controls module (tests/ is not an importable package)."""
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location(
        "grounding_controls", Path(__file__).parent / "grounding_controls.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod.ALL_CONTROLS


def rubric_of(control) -> Rubric:
    return Rubric(
        id=f"{control.name}_v1",
        items=[RubricItem(id=i, criterion=c) for i, c in control.rubric_items],
    )


def record(*, allow_compute: bool = True) -> VerdictCassette:
    cassette = VerdictCassette(CASSETTE_PATH, model_id=JUDGE_MODEL, allow_compute=allow_compute)
    judge = OpenRouterJudge(client=OpenRouterClient(model=JUDGE_MODEL), cassette=cassette)
    for control in _import_controls():
        rubric = rubric_of(control)
        for label, answer in (("grounded", control.grounded_answer), ("fabricated", control.fabricated_answer)):
            result = judge(rubric, EvalContext(case_id=control.name, output=answer), control.reference)
            print(f"{control.name:32} {label:10} {control.key_item}={result.per_item[control.key_item]:.2f}")
    return cassette


if __name__ == "__main__":
    from knowledge.evals.run import load_env

    load_env()
    record()
    print(f"\nwrote {CASSETTE_PATH}")
