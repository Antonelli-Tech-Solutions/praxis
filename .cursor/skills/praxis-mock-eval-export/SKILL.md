---
name: praxis-mock-eval-export
description: Keep PRAXIS mock data, eval cases, dashboard fixtures, and the Render seed in sync. Use when editing frontend/mock_data.py or knowledge/evals/cases, adding hand-crafted demo rows, fixing stale mock-candidates.json, or preparing a Render deploy.
---

# PRAXIS mock / eval / fixture export

Canonical source of truth for dashboard demo data is **`frontend/mock_data.py`**.
Everything else is generated. A recurring bug: editing mock data or eval cases but
forgetting to re-export, so committed fixtures and Render go stale. Always
re-export and re-test after changing either side.

## The data graph

```
frontend/mock_data.py  ──(export scripts)──▶  frontend-react/public/*.json
        ▲                                      knowledge/serve/data/pipeline-candidates.json (API seed)
        │
frontend/eval_mock_bridge.py (HAND_CRAFTED_EVAL_CASE_IDS)
        │
knowledge/evals/cases/<case_id>/case.yaml  (flat layout; e.g. matt/, monica/, quirky_*, poison_*)
```

Provenance on every candidate uses the format `logs/<file>.jsonl:<line>`.

## After editing mock data OR eval cases

Run from the repo root:

```powershell
# Dashboard mock fixtures (React mock mode + eval metrics)
uv run python scripts/export-mock-candidates.py
# Render seed (React public JSON + API store seed on first boot)
uv run python scripts/export-render-seed.py
```

Outputs:
- `frontend-react/public/mock-candidates.json`
- `frontend-react/public/mock-graph.json`
- `frontend-react/public/mock-eval-metrics.json`
- `knowledge/serve/data/pipeline-candidates.json` (Render API seed)

## Then prove alignment

```powershell
uv run pytest frontend/tests/test_mock_eval_alignment.py -q
uv run pytest frontend/tests/ -q
uv run pytest knowledge/evals/tests/test_cases.py -q
```

`test_mock_eval_alignment.py` asserts `mock_data.py` rows match the eval case
registry. If you add a hand-crafted demo row that mirrors a real eval case, add
its id to `HAND_CRAFTED_EVAL_CASE_IDS` in `frontend/eval_mock_bridge.py` and
mirror it in `knowledge/evals/cases/MATTHEW_HANDOFF.md`.

## Commit

**Stage the regenerated JSON fixtures** alongside the source change in the same
commit — never leave `mock-candidates.json` lagging behind `mock_data.py`. Then
ship via the `ship-praxis-work` skill.

## Boundaries

Authoring eval cases for Matthew is add-only: create new files under
`knowledge/evals/cases/`, extend deterministic checks if needed, but do not edit
`eval_def.py`, `run.py`, or `serve/app.py`. See `.cursor/rules/praxis-guardrails.mdc`.
