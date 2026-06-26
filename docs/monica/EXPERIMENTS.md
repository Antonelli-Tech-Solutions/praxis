# Monica Human-Gate Experiment Menu

**Owner:** Monica Peters
**Updated:** 2026-06-25
**Scope:** Potential experiments for discussing and demonstrating the Dashboard & Human Gate pillar.

This menu is grounded in:

- [DEMO_SCRIPT.md](DEMO_SCRIPT.md)
- [INTEGRATION_SMOKE.md](INTEGRATION_SMOKE.md)
- [REHEARSAL_LOG.md](REHEARSAL_LOG.md)
- [PRAXIS_Project_Plan.html](../plans/PRAXIS_Project_Plan.html)
- [proposal-praxis.pdf](../plans/proposal-praxis.pdf)
- `knowledge/evals/cases/monica/README.md`

The core comparison is:

```text
AI autonomous decision or auto-memory
vs.
human-gated, data-led knowledge promotion
```

Use these experiments to support the project demo story: raw logs produce candidate lessons, reviewers inspect evidence and confidence, humans approve only trustworthy knowledge, and the eval layer measures whether approved knowledge improves later outcomes.

## Experiment List

| # | Experiment | Compare | Purpose / Reason |
|---|---|---|---|
| 1 | Cold vs knowledge-injected agent run | No PRAXIS context vs human-approved active knowledge injected | Prove the core project claim: approved knowledge should reduce corrections, repeated failures, tokens, and time without lowering success rate. |
| 2 | Autonomous memory vs human-gated knowledge | AI auto-saves and injects lessons vs reviewer approves credible candidates | Show why a human gate matters. Autonomous memory can compound wrong or over-generalized lessons; human review can reduce that risk. |
| 3 | Proposed-only vs active-only injection | Inject all distilled candidates vs inject only `active` human-approved candidates | Demonstrate the lifecycle invariant: passively distilled knowledge should not influence future runs until a human approves it. |
| 4 | Low-confidence promotion test | Human confirms a low-confidence candidate vs system auto-promotes it | Show how confidence warnings prevent weak evidence from becoming reusable knowledge. This is important for high-impact decisions in organizations and communities. |
| 5 | Contradiction-resolution test | Silent conflict in memory vs visible human contradiction decision | Demonstrate that conflicting lessons should be surfaced as reviewable pairs before reuse, not hidden inside memory. |
| 6 | Provenance trust test | Candidate shown without source evidence vs candidate with `logs/...jsonl:line` provenance | Measure whether reviewers make better or more confident decisions when every lesson links back to evidence. |
| 7 | Confidence-breakdown test | Opaque confidence score vs frequency, recency, and breadth breakdown | Show that data-led decisions improve when reviewers can challenge the score rather than accept a black-box number. |
| 8 | Human-gate latency vs safety tradeoff | Instant autonomous promotion vs slower human approval | Quantify the cost of review time against the benefit of avoiding bad promotions. Useful for discussing safety-sensitive organizational decisions. |
| 9 | Audit-trail accountability test | Mutation without audit trail vs promote/reject/resolve with actor, timestamp, and state history | Show governance value: reviewers and organizations can explain who approved what, when, and why. |
| 10 | Mock vs live API decision safety | Stable mock fixtures vs disposable live API mutations | Demonstrate that Monica's UI can be rehearsed safely while live mutation tests are reserved for disposable data. |
| 11 | Data-source fallback experiment | Live API unavailable with unclear UX vs clear mock/live source state | Show resilience and transparency: users should know whether decisions are based on live organizational data or mock demo data. |
| 12 | Eval visibility experiment | Dashboard hides metrics vs dashboard exposes or links eval evidence | Show that human approval alone is not enough; future outcomes must be measured after knowledge is injected. |
| 13 | Cross-domain transfer framing | Coding-only lessons vs same loop applied to research, writing, data, and operations workflows | Discuss why the approach can generalize beyond software if the workflow has logs, evidence, approval, and measured reuse. |
| 14 | Community-impact simulation | AI-only decision suggestions vs human-gated, evidence-backed suggestions | Discuss possible United States use cases such as school services, nonprofit intake, public-benefit triage, family resource planning, healthcare administration, legal aid routing, workforce support, and civic operations. Frame this as a simulation unless real participant and outcome data are collected. |

## Best Demo Set

For a concise project demo, prioritize:

1. **Cold vs knowledge-injected agent run** - proves the measurable value claim.
2. **Autonomous memory vs human-gated knowledge** - explains why Monica's pillar exists.
3. **Proposed-only vs active-only injection** - proves unapproved knowledge is staged, not injected.
4. **Contradiction-resolution test** - shows how the dashboard prevents silent conflict.
5. **Confidence-breakdown test** - shows data-led review rather than blind approval.
6. **Audit-trail accountability test** - shows governance and explainability.
7. **Eval visibility experiment** - hands cleanly to Dominic's measured proof.

## Current Repo Support

The most directly supported Monica experiments are already represented by the focused eval suite under `knowledge/evals/cases/monica/`:

| Existing case | Supports experiment |
|---|---|
| `monica_demo_candidate_contract` | Provenance trust, confidence-breakdown review, candidate contract readiness |
| `monica_human_gate_staged_not_injected` | Proposed-only vs active-only injection |
| `monica_promotion_context_cand1` | Human-approved knowledge becoming future context |
| `monica_contradiction_pair_metadata` | Contradiction-resolution test |
| `monica_api_mutation_audit_trail` | Audit-trail accountability |
| `monica_low_confidence_confirmation` | Low-confidence promotion test |
| `monica_data_source_fallback_readiness` | Mock/live source safety and fallback transparency |
| `monica_eval_metrics_narrative` | Eval visibility and correction-reduction narrative |

Verify the Monica eval suite from the repository root:

```powershell
uv run pytest knowledge/evals/tests/test_monica_suite.py -q
```

Run the broader Monica gate when preparing final demo evidence:

```powershell
uv run pytest knowledge/evals/tests/test_cases.py frontend/tests/ -q

Push-Location frontend-react
npm test
npm run lint
npm run build
Pop-Location
```

The `npm` commands must run from `frontend-react/`; the repository root does not have a `package.json`.

## Social Impact Framing

The strongest discussion point is not that humans should manually approve every AI action. It is that high-impact reusable knowledge should be:

- evidence-linked,
- confidence-scored,
- contradiction-checked,
- explicitly approved when risk is high,
- auditable after mutation,
- measured against later outcomes.

For societies, communities, organizations, families, and individuals in the United States, the relevant question is:

```text
When AI decisions compound across future actions, what safeguards keep one bad lesson from becoming repeated harm?
```

PRAXIS answers that question with a human gate, provenance, confidence review, contradiction resolution, and eval evidence. Any claims about real social outcomes should be presented as future research or simulation unless the team has collected real-world outcome data.
