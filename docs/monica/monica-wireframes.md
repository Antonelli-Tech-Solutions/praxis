# Monica Peters — Dashboard As-Built Spec

**Author:** Monica Peters <monigarr@MoniGarr.com>  
**Branch:** `monica/dashboard-human-gate`  
**Created:** 2026-06-17  
**Last updated:** 2026-06-18  
**Status:** As-built for shipped UI on this branch (Day 2 shell + partial Day 3).

Architecture source of truth: [CONFIDENTIAL_PRAXIS_Project_Plan.html](../PRAXIS_Project_Plan.html).

Pillar architecture: [ARCHITECTURE_MONICA.md](ARCHITECTURE_MONICA.md).

## Overview

The human-gate dashboard is a **modular Streamlit app** under `frontend/`. Entry point `app.py` wires a `DataProvider` to UI components; it does not contain presentation logic.

```text
frontend/app.py
  → components/candidate_list.py      (table + card views)
  → components/candidate_detail.py    (detail expander)
  → components/eval_metrics_embed.py  (placeholder curve)
  → services/data_provider.py         (mock or API factory)
```

Lifecycle states: `proposed → suggested → active` (plus `decayed` and unrecognized API values preserved for display).

## Screen 1: Dashboard shell + candidate list (shipped)

**File:** `frontend/app.py`, `frontend/components/candidate_list.py`

| Element | Implementation |
|---------|----------------|
| Header | `st.title("Candidate Review Gate")` + subtitle markdown |
| Mode banner | Mock vs live API caption from `PRAXIS_API_BASE_URL` |
| Search | `st.text_input` — filters title and content (case-insensitive) |
| State filter | `st.selectbox` — All / proposed / suggested / active |
| Table tab | `st.dataframe` with `ProgressColumn` for confidence; shared Promote/Reject row |
| Card tab | `st.columns(3)` grid, `st.container(border=True)` per candidate |
| State badge | `confidence_badge.render_state_badge` — orange/blue/green/gray |
| Confidence | `st.progress` on cards; `ProgressColumn` in table |
| Provenance | `st.caption` with `` `logs/<file>.jsonl:<line>` `` |
| Actions | Promote advances one lifecycle step; Reject removes from mock queue |
| Footer | Pillar + integration note |

**Mock data:** 17 candidates in `frontend/mock_data.py` (5 generic + 12 nushell session-derived). All provenance uses `logs/<file>.jsonl:<line>`.

## Screen 2: Candidate detail (partial Day 3 — shipped)

**File:** `frontend/components/candidate_detail.py`

| Element | Implementation |
|---------|----------------|
| Container | `st.expander("Candidate detail (Day 3)")`, expanded when list non-empty |
| Selector | `st.selectbox` to inspect any filtered candidate |
| Content | Full title, state, provenance, body |
| Confidence | `render_confidence_breakdown` — metrics when breakdown present; placeholder progress bar otherwise |
| Audit trail | Caption with `created_at`; full JSONL audit wiring Days 6–7 |
| Extra fields | `st.expander("Additional pipeline fields")` shows `Candidate.extra` for unknown API keys |
| Contradictions | `contradiction_panel.py` when `contradiction_ids` set (layout stub; mutations Days 6–7) |

## Screen 3: Eval metrics embed (Day 8 placeholder — shipped)

**File:** `frontend/components/eval_metrics_embed.py`

- Collapsed expander with placeholder `st.line_chart` correction-rate curve.
- Dominic owns computation in `eval/`; dashboard renders API/JSON only.

## Data contract (forward-compatible)

`frontend/models/candidate.py` — `Candidate.from_mapping()` is the integration surface.

### Required for display (defaults if absent)

| Field | Aliases accepted | Notes |
|-------|------------------|-------|
| `id` | — | Stable identifier |
| `title` | — | Distilled lesson title |
| `content` | — | Full lesson body |
| `state` | — | Known: `proposed`, `suggested`, `active`, `decayed`; unknown values shown as-is (gray badge) |
| `confidence` | — | Float 0–1; defaults to `0.0` |
| `provenance` | `source`, `source_log`, `sourceLog` | Canonical display: `logs/<file>.jsonl:<line>` |
| `createdAt` | `created_at`, `updatedAt`, `updated_at` | ISO 8601 |

### Optional (pipeline extensions)

| Field | Aliases | Notes |
|-------|---------|-------|
| `confidenceBreakdown` | `confidence_breakdown` | `{ frequency, recency, breadth }` + optional rationale strings |
| `contradictions` | `contradiction_ids` | List of ids or `{ id }` objects |
| *any other key* | — | Preserved in `Candidate.extra` and shown in detail view |

**Versioning:** HTTP client sends `X-Praxis-Contract: 1`. Matthew/Dominic may extend the schema; Monica's pillar must not break on unknown fields.

### Mutations (Days 6–7)

| Action | Endpoint |
|--------|----------|
| Promote | `POST /candidates/{id}/promote` |
| Reject | `POST /candidates/{id}/reject` |
| Resolve contradiction | `POST /contradictions/{id}/resolve` |

Stub: `frontend/services/api_client.py`.

## Design notes

- Streamlit-native layout — no custom CSS framework
- Theme: `frontend/.streamlit/config.toml` (light, high-contrast defaults)
- Keyboard/a11y polish targeted Days 8–10

## Remaining (not yet on this branch)

| Day | Item |
|-----|------|
| 4 | Workflow polish (confirmations, state transitions UX) |
| 5 | Contradiction resolution actions + live credibility breakdown from pipeline |
| 6–7 | `ApiDataProvider` HTTP wire-up, audit trail from backend |
| 8 | Real eval metrics from Dominic's API |
| 9–10 | Demo polish, user-flow video |
