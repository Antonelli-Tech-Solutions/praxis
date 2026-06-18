## Team Blueprint (Copy/Paste)

### Team: `DT-XXX - Team Name`

**Purpose:**  
One sentence on what this team is optimized for.

**Hypothesis:**  
What you expect this team to do better than baseline.

**When To Use:**  
Short rule of thumb for selecting this team in the dashboard.

#### Agent Roles

| Role | Agent Name | Model | Function | Trust Level |
|---|---|---|---|---|
| Orchestrator |  |  |  |  |
| Red Team |  |  |  |  |
| Judge |  |  |  |  |
| Documentation |  |  |  |  |
| Regression |  |  |  |  |
| Cost/Safety |  |  |  |  |

#### Run Notes + Scorecard

| Date | Target | Seeds Used | Pass Rate | High Sev Findings | Avg Cost/Run | Avg Runtime | Verdict Quality | Keep? |
|---|---|---|---:|---:|---:|---:|---|---|
| YYYY-MM-DD |  |  |  |  |  |  | 1-10 | Yes / No |

**Observations:**  
- What worked:
- What failed:
- What to change next:


## Current Baseline Team

### Team: `DT-001 - Tiered Core Six`

**Purpose:**  
Balanced cost, safety, and judgment quality for regular dashboard attack test runs.

**Hypothesis:**  
Using cheaper high-volume mutation with stronger judgment should maximize useful findings per dollar.

**When To Use:**  
Default choice for daily runs and first-pass comparisons.

#### Agent Roles

| Role | Agent Name | Model | Function | Trust Level |
|---|---|---|---|---|
| Orchestrator | CoverageCommander | Gemini 3 Flash or hosted GPT-3.5-class API | Prioritizes tests, coverage gaps, stop conditions, and regression triggers | Medium |
| Red Team | AdversaryForge | Gemini 3 Flash (OpenRouter) | Generates and mutates attack cases from seeds | Low |
| Judge | VerdictGuard | Gemini 3 Pro | Independent pass/fail rubric evaluation | Medium-low |
| Documentation | ReportScribe | GPT-5.2 Codex or Gemini 3 Pro | Converts verdicts into structured vulnerability reports | Medium-low |
| Regression | ReplayGate | Model optional (deterministic preferred) | Replays confirmed findings with deterministic tests | High |
| Cost/Safety | BudgetSentinel | Deterministic policy logic | Enforces rate limits, token budgets, target health checks, kill switch | High |

#### Model Cost Snapshot (Approximate)

| Role Focus | Recommended Model | Why | Approx Cost per 1K Runs |
|---|---|---|---:|
| Red Team mutation | Gemini 3 Flash (OpenRouter) | Cost-efficient for high-volume mutation | ~$50 |
| Judge agent | Gemini 3 Pro | Better precision where verdict errors are expensive | ~$200-$500 |
| Documentation | GPT-5.2 Codex or Gemini 3 Pro | Strong structured output for technical reports | ~$200 |
| Orchestrator | Gemini 3 Flash or hosted GPT-3.5-class API | Light routing and control logic | ~$20 |

#### Run Notes + Scorecard

| Date | Target | Seeds Used | Pass Rate | High Sev Findings | Avg Cost/Run | Avg Runtime | Verdict Quality | Keep? |
|---|---|---|---:|---:|---:|---:|---|---|
| 2026-05-13 | Staging baseline | Prompt injection, indirect injection, data exfiltration |  |  |  |  |  | Yes |

**Observations:**  
- What worked:  
- What failed:  
- What to change next:  

---

## Team Comparison Board

Use this block to choose your next "best" team quickly.

| Team ID | Findings Quality (1-10) | Cost Efficiency (1-10) | Stability (1-10) | Speed (1-10) | Overall (avg) | Verdict |
|---|---:|---:|---:|---:|---:|---|
| DT-001 |  |  |  |  |  | Baseline |
| DT-002 |  |  |  |  |  |  |
| DT-003 |  |  |  |  |  |  |

**Best Team Right Now:** `TBD`  
**Reason:** `TBD`