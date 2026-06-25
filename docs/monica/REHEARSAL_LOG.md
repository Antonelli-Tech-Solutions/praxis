# Monica Rehearsal Log - Dashboard & Human Gate

Updated: 2026-06-25

Plan alignment: [PRAXIS_Project_Plan.html](../plans/PRAXIS_Project_Plan.html) names Monica as **Dashboard & Human Gate Lead**. Monica's scope is the React dashboard in `frontend-react/` plus the Python contract layer in `frontend/`: human approval workflow, provenance, confidence review, contradiction resolution UI, and dashboard evidence for knowledge promotion.

Team timing constraint: Monica's demo segment is capped at about **2 minutes** so Matthew can present the ML/Knowledge Pipeline pillar and Dominic can present the Architecture/Eval/Integration pillar.

## Capstone Story Alignment

Dominic's original demo arc is: **Dumb Agent -> PRAXIS learns from the run -> Smart Agent**. Monica's segment should support that story as the trust checkpoint in the middle, not replace Matthew's pipeline explanation or Dominic's measured proof.

| Team beat | Owner | Monica support |
|---|---|---|
| Dumb Agent baseline | Dominic | Do not spend Monica time proving the baseline; reference that the dashboard starts after raw run evidence has produced candidates. |
| Candidate creation and knowledge substrate | Matthew | Show candidate evidence, confidence, and provenance as the review surface for Matthew's pipeline output. |
| Human gate | Monica | Demonstrate that proposed lessons become usable knowledge only through transparent human approval and contradiction resolution. |
| Smart Agent / compounding proof | Dominic | Hand off cleanly to eval results showing whether approved knowledge reduces corrections on future runs. |

Use current repository lifecycle language in Monica's segment: `proposed -> active` and `rejected`. The project plan's older `proposed -> suggested -> active` wording represents the same human-gate intent, but the current code and demo docs should use the implemented states.

## Current Repo State

Evidence checked from the current repository:

- `frontend-react/src/types/candidate.ts` defines candidate states as `proposed`, `active`, and `rejected`.
- `frontend-react/src/api/mockGateWorkflow.test.ts` covers at least 18 mock candidates, `cand_1` promotion to `active`, the `cand_9` / `cand_16` contradiction pair, rejected-state behavior, and contradiction resolution.
- `frontend/mock_data.py` provides demo candidates with provenance, confidence breakdowns, audit trails, and contradiction data.
- `frontend-react/src/config/dataSource.ts` defaults local startup to the Local Postgres live preset at `http://localhost:8000`; mock fixtures still exist, but the demo should explicitly confirm the selected data source before starting.
- `docs/monica/DEMO_SCRIPT.md`, `MONICA_COMPLETION_PATH.md`, and `INTEGRATION_SMOKE.md` now describe the current `proposed -> active` / `rejected` lifecycle.

No full test gate was rerun during this documentation update. Before the final recorded demo, rerun the gate below and replace the older 2026-06-19 result.

## Validation Gate To Rerun

Run from repo root:

```powershell
uv run pytest frontend/tests/ knowledge/evals/tests/test_cases.py -q
cd frontend-react
npm test
npm run lint
npm run build
```

Record the final result here:

| Date | Commands | Result | Notes |
|---|---|---|---|
| 2026-06-19 | `uv run pytest knowledge/evals/tests/test_cases.py frontend/tests/ -q`; `cd frontend-react && npm run lint && npm run build` | Passed: 35 pytest checks; lint/build OK | Historical gate. Rerun before final recording. |
| 2026-06-25 | Documentation alignment only | Not run | Updated rehearsal scope to current repo lifecycle and 2-minute Monica segment. |

## Two-Minute Monica Segment

Target duration: 1:45-2:00.

| Time | Beat | Screen/action | Say |
|---|---|---|---|
| 0:00-0:15 | Role setup | Dashboard open; confirm data source | "Dominic's demo arc is dumb agent to smart agent. My pillar is the trust checkpoint in the middle: the Dashboard and Human Gate where distilled candidate lessons become auditable, human-approved knowledge." |
| 0:15-0:40 | Provenance and confidence | Select `cand_1`; show detail, provenance, confidence breakdown | "This is Matthew's pipeline output at the review boundary. The dashboard does not ask reviewers to trust an opaque score; it shows source evidence, confidence, and an audit trail before promotion." |
| 0:40-1:10 | Human promotion | Promote `cand_1` from `proposed` to `active` | "The key control is explicit human approval. A candidate moves from proposed to active only after a reviewer confirms it." |
| 1:10-1:35 | Contradiction handling | Open `cand_9` / `cand_16`; keep the stronger candidate | "When lessons conflict, the UI makes the contradiction visible and forces a human decision instead of silently compounding bad memory." |
| 1:35-1:55 | Team handoff | Point to graph/eval/data-source area | "My dashboard is the gate. Matthew owns the pipeline that creates and stores these candidates, and Dominic owns the dumb-agent versus smart-agent eval proof that promoted knowledge improves future runs." |
| 1:55-2:00 | Handoff | Stop sharing or pass narration | "I am handing off to the pipeline and eval pillars." |

## Rehearsal Checklist

- [ ] Confirm the selected data source before starting: mock fixtures for a stable portfolio demo, or disposable local API data if using Local Postgres.
- [ ] Keep Monica's segment at or below 2 minutes.
- [ ] Show only Monica-owned UI and contract behavior; do not explain Matthew's pipeline internals or Dominic's eval harness beyond the handoff sentence.
- [ ] Use current lifecycle language: `proposed -> active`, `rejected`.
- [ ] Show provenance and confidence before promotion.
- [ ] Show one contradiction decision only; do not spend time exploring all graph features.
- [ ] End with a clean handoff to Matthew/Dominic.

## Evidence To Capture

Store small screenshots under `docs/monica/screenshots/` or link external media here if the file is large.

| Evidence | Status | Notes |
|---|---|---|
| Data-source state | Pending | Capture before timing starts. |
| `cand_1` detail with provenance/confidence | Pending | Main proof for transparent review. |
| Promote confirmation / success state | Pending | Shows `proposed -> active`. |
| `cand_9` / `cand_16` contradiction before/after | Pending | Shows human conflict resolution. |
| 2-minute screen recording | Pending | Keep Monica-only segment under 2 minutes. |

## Demo Boundaries

Monica should not cover:

- Matthew's ingestion, distillation, deduplication, confidence-scoring internals, or Knowledge Graph persistence details.
- Dominic's eval harness implementation, replay methodology, GitHub hook automation, or compounding-curve proof.
- Render/RDS setup unless asked directly during Q&A.

Monica should cover:

- Why a human gate is needed.
- How reviewers inspect evidence and confidence.
- How explicit approval promotes knowledge.
- How contradiction resolution prevents bad lessons from compounding.
- How the dashboard hands cleanly into Matthew's and Dominic's pillars.
