# Monica Experiment Demo Video Scripts

**Owner:** Monica Peters
**Updated:** 2026-06-25
**Source experiment menu:** [EXPERIMENTS.md](EXPERIMENTS.md)
**Target duration:** each original spoken script is planned for about 75-100 seconds; generated captioned MP4s for experiments 1-14 stay under the current 2 minutes 50 seconds cap. Experiment 15 is a 3-minute composite poison-quarantine demo.

These scripts turn each experiment in `EXPERIMENTS.md` into a short screen-recording plan with spoken narration. They are grounded in the current Monica dashboard and eval support:

- Dashboard screenshots: `docs/monica/screenshots/demo-capture-2026-06-25/`
- Core demo flow: [DEMO_SCRIPT.md](DEMO_SCRIPT.md)
- Rehearsal timing: [REHEARSAL_LOG.md](REHEARSAL_LOG.md)
- Eval cases: `knowledge/evals/cases/monica/`

Voiceover note: do not store text-to-speech API keys in this repository. If ElevenLabs voiceover is added later, set the key in a local environment variable and keep the generated audio out of source control unless the team explicitly wants to track it.

Generated video note: the current MP4s are captioned slide videos with a silent audio track, built from repo-local Monica screenshots. Experiment 1 uses the reviewed zoom treatment at about 55 seconds; experiments 2-14 use the same treatment at about 75-90 seconds each. Add recorded narration or ElevenLabs voiceover as a final editing pass after the API key is configured safely outside the repo.

Generated video folder:

`docs/monica/videos/experiment-video-capture-2026-06-25/`

## Experiment Coverage Map

| # | Experiment | Demo video | Support level |
|---|---|---|---|
| 1 | Cold vs knowledge-injected agent run | [experiment-01-cold-vs-knowledge-injected-agent-run.mp4](videos/experiment-video-capture-2026-06-25/experiment-01-cold-vs-knowledge-injected-agent-run.mp4) | Eval narrative support |
| 2 | Autonomous memory vs human-gated knowledge | [experiment-02-autonomous-memory-vs-human-gated-knowledge.mp4](videos/experiment-video-capture-2026-06-25/experiment-02-autonomous-memory-vs-human-gated-knowledge.mp4) | Dashboard and framing support |
| 3 | Proposed-only vs active-only injection | [experiment-03-proposed-only-vs-active-only-injection.mp4](videos/experiment-video-capture-2026-06-25/experiment-03-proposed-only-vs-active-only-injection.mp4) | Direct eval support |
| 4 | Low-confidence promotion test | [experiment-04-low-confidence-promotion-test.mp4](videos/experiment-video-capture-2026-06-25/experiment-04-low-confidence-promotion-test.mp4) | Direct eval support |
| 5 | Contradiction-resolution test | [experiment-05-contradiction-resolution-test.mp4](videos/experiment-video-capture-2026-06-25/experiment-05-contradiction-resolution-test.mp4) | Direct eval and UI support |
| 6 | Provenance trust test | [experiment-06-provenance-trust-test.mp4](videos/experiment-video-capture-2026-06-25/experiment-06-provenance-trust-test.mp4) | Direct contract support |
| 7 | Confidence-breakdown test | [experiment-07-confidence-breakdown-test.mp4](videos/experiment-video-capture-2026-06-25/experiment-07-confidence-breakdown-test.mp4) | Direct contract support |
| 8 | Human-gate latency vs safety tradeoff | [experiment-08-human-gate-latency-vs-safety-tradeoff.mp4](videos/experiment-video-capture-2026-06-25/experiment-08-human-gate-latency-vs-safety-tradeoff.mp4) | Dashboard and discussion support |
| 9 | Audit-trail accountability test | [experiment-09-audit-trail-accountability-test.mp4](videos/experiment-video-capture-2026-06-25/experiment-09-audit-trail-accountability-test.mp4) | Direct eval and contract support |
| 10 | Mock vs live API decision safety | [experiment-10-mock-vs-live-api-decision-safety.mp4](videos/experiment-video-capture-2026-06-25/experiment-10-mock-vs-live-api-decision-safety.mp4) | Integration smoke support |
| 11 | Data-source fallback experiment | [experiment-11-data-source-fallback-experiment.mp4](videos/experiment-video-capture-2026-06-25/experiment-11-data-source-fallback-experiment.mp4) | Direct eval support |
| 12 | Eval visibility experiment | [experiment-12-eval-visibility-experiment.mp4](videos/experiment-video-capture-2026-06-25/experiment-12-eval-visibility-experiment.mp4) | Direct eval support |
| 13 | Cross-domain transfer framing | [experiment-13-cross-domain-transfer-framing.mp4](videos/experiment-video-capture-2026-06-25/experiment-13-cross-domain-transfer-framing.mp4) | Framing only |
| 14 | Community-impact simulation | [experiment-14-community-impact-simulation.mp4](videos/experiment-video-capture-2026-06-25/experiment-14-community-impact-simulation.mp4) | Simulation framing only |
| 15 | Poisoned source quarantine test | [experiment-15-poisoned-source-quarantine-test.mp4](videos/experiment-video-capture-2026-06-25/experiment-15-poisoned-source-quarantine-test.mp4) | Composite frontend gate, candidate API, and eval handoff support |

## 1. Cold vs Knowledge-Injected Agent Run

**Purpose:** Prove the central PRAXIS claim: approved knowledge should reduce corrections, repeated failures, tokens, and time without lowering success rate.

**Screenshots:** `09-load-eval-data-handoff.png`, `03-cand1-provenance-confidence.png`, `05-after-confirm-approve.png`

| Time | Show on screen | Speak |
|---|---|---|
| 0:00-0:12 | Title card with the comparison: cold run vs human-approved context. | "This experiment asks whether PRAXIS makes an agent measurably better after a human-approved lesson is available." |
| 0:12-0:32 | Eval handoff screenshot. Point to the eval evidence area. | "The cold run starts without PRAXIS context. The knowledge-injected run gets only active, approved knowledge, not raw memory or unreviewed suggestions." |
| 0:32-0:55 | Candidate detail showing `cand_1`, provenance, confidence, and audit trail. | "The approved lesson is evidence-linked. Reviewers can inspect the original log line, confidence score, and audit trail before it becomes reusable context." |
| 0:55-1:18 | Post-approval screenshot showing the human gate result. | "The expected win is fewer repeated corrections and lower wasted time, while maintaining the same success standard." |
| 1:18-1:30 | Closing card: measured improvement requires eval proof. | "This is the clean handoff to Dominic's eval layer: Monica's dashboard controls what is allowed into the injected context." |

## 2. Autonomous Memory vs Human-Gated Knowledge

**Purpose:** Show why a human gate matters when reusable memory can compound errors.

**Screenshots:** `04-approval-action.png`, `06-contradictions-review.png`, `03-cand1-provenance-confidence.png`

| Time | Show on screen | Speak |
|---|---|---|
| 0:00-0:12 | Title card: autonomous memory vs human gate. | "This experiment compares automatic memory promotion against PRAXIS's human-gated knowledge flow." |
| 0:12-0:32 | Candidate detail with provenance and score. | "Autonomous memory can save a plausible lesson quickly, but speed is not the same as trust. A wrong lesson can be reused again and again." |
| 0:32-0:58 | Approval dialog screenshot. | "In the human-gated path, the reviewer sees the candidate, confidence, evidence, and state before it becomes active." |
| 0:58-1:18 | Contradiction review screenshot. | "If the system finds a conflict, it is surfaced as a decision, not buried in memory." |
| 1:18-1:32 | Closing card: trust checkpoint. | "The point is not to slow every AI action. The point is to gate high-impact reusable knowledge before it compounds." |

## 3. Proposed-Only vs Active-Only Injection

**Purpose:** Demonstrate the lifecycle invariant: distilled candidates should not influence future runs until a human approves them.

**Screenshots:** `03-cand1-provenance-confidence.png`, `04-approval-action.png`, `05-after-confirm-approve.png`

| Time | Show on screen | Speak |
|---|---|---|
| 0:00-0:12 | Title card: proposed is staged, active is injectable. | "This experiment protects the most important lifecycle rule in Monica's pillar." |
| 0:12-0:34 | Candidate detail showing `cand_1` as proposed with evidence. | "A proposed candidate is visible for review. It can be inspected, challenged, rejected, or approved, but it should not be injected into future agent context yet." |
| 0:34-0:58 | Approval confirmation. | "The state changes only when a reviewer explicitly confirms the promotion." |
| 0:58-1:18 | Post-approval active state. | "After approval, the lesson becomes active and eligible for reuse." |
| 1:18-1:30 | Closing card: invariant. | "The experiment passes when proposed-only injection is blocked and active-only injection is allowed." |

## 4. Low-Confidence Promotion Test

**Purpose:** Show that weak evidence needs an explicit review checkpoint before becoming reusable knowledge.

**Screenshots:** `04-approval-action.png`, `03-cand1-provenance-confidence.png`, `05-after-confirm-approve.png`

| Time | Show on screen | Speak |
|---|---|---|
| 0:00-0:12 | Title card: low confidence requires confirmation. | "This experiment focuses on the cases where evidence exists, but the score is not strong enough to trust automatically." |
| 0:12-0:34 | Candidate detail and confidence breakdown. | "The reviewer should see why the score is low or mixed. Frequency, recency, and breadth should be open to inspection." |
| 0:34-0:58 | Approval dialog. | "If a reviewer still promotes the candidate, the action should be deliberate, confirmed, and auditable." |
| 0:58-1:18 | Post-approval state or audit trail. | "The dashboard should not hide uncertainty. It should make the risk visible before promotion." |
| 1:18-1:30 | Closing card: confidence is a warning, not a verdict. | "The goal is to prevent weak evidence from silently becoming organizational memory." |

## 5. Contradiction-Resolution Test

**Purpose:** Demonstrate that conflicting lessons are surfaced as reviewable pairs before reuse.

**Screenshots:** `06-contradictions-review.png`, `07-after-keep-this-cand9.png`, `08-deferred-contradiction.png`

| Time | Show on screen | Speak |
|---|---|---|
| 0:00-0:12 | Title card: visible conflict beats silent conflict. | "This experiment shows how PRAXIS handles two lessons that cannot both be universally true." |
| 0:12-0:36 | Contradiction view for `cand_9` and `cand_16`. | "The dashboard shows the conflict as a pair: one lesson says startup flags must be set before config load, and the rival says config is the normal path for day-to-day flags." |
| 0:36-0:58 | Keep-this result screenshot. | "A reviewer can keep the stronger lesson, reject the rival, or write a custom resolution." |
| 0:58-1:18 | Deferred contradiction screenshot. | "If the evidence is not enough, the reviewer can defer instead of forcing a bad decision." |
| 1:18-1:32 | Closing card: no hidden conflicts. | "The pass condition is simple: contradictions must be visible before they are reused." |

## 6. Provenance Trust Test

**Purpose:** Measure whether reviewers make better decisions when every candidate links back to source evidence.

**Screenshots:** `03-cand1-provenance-confidence.png`, `02-data-source-dashboard.png`

| Time | Show on screen | Speak |
|---|---|---|
| 0:00-0:12 | Title card: evidence-linked review. | "This experiment compares a lesson shown alone against a lesson shown with source provenance." |
| 0:12-0:36 | Candidate detail with `logs/...jsonl:line` provenance. | "The current Monica contract includes a provenance field on each candidate. That turns a claim into something a reviewer can trace." |
| 0:36-0:58 | Confidence and audit trail area. | "The reviewer can see what the pipeline distilled, when it scored it, and where the original evidence came from." |
| 0:58-1:18 | Data-source screenshot. | "The data source matters too. A reviewer should know whether this evidence came from a stable mock fixture or a live API." |
| 1:18-1:30 | Closing card: trust requires traceability. | "A candidate without evidence is just advice. A candidate with provenance can be reviewed." |

## 7. Confidence-Breakdown Test

**Purpose:** Show that a score is more useful when reviewers can inspect frequency, recency, and breadth.

**Screenshots:** `03-cand1-provenance-confidence.png`, `04-approval-action.png`

| Time | Show on screen | Speak |
|---|---|---|
| 0:00-0:12 | Title card: from black-box score to inspectable score. | "This experiment compares an opaque confidence score with an inspectable confidence breakdown." |
| 0:12-0:38 | Candidate detail showing frequency, recency, and breadth. | "The reviewer can challenge the components. Was the lesson frequent enough? Was it recent? Did it apply across enough workflows?" |
| 0:38-0:58 | Approval dialog. | "That matters before approval, because promotion turns a candidate into reusable context." |
| 0:58-1:18 | Detail or audit area. | "The dashboard does not ask for blind trust in a number. It gives reviewers the pieces behind the number." |
| 1:18-1:30 | Closing card: data-led review. | "The pass condition is that the reviewer can explain the score before acting on it." |

## 8. Human-Gate Latency vs Safety Tradeoff

**Purpose:** Quantify the cost of review time against the benefit of avoiding bad promotions.

**Screenshots:** `04-approval-action.png`, `05-after-confirm-approve.png`, `06-contradictions-review.png`

| Time | Show on screen | Speak |
|---|---|---|
| 0:00-0:12 | Title card: speed vs safety. | "This experiment frames the tradeoff between instant promotion and a slower human review." |
| 0:12-0:34 | Approval confirmation screenshot. | "The human gate adds latency. A reviewer has to inspect evidence and confirm the action." |
| 0:34-0:58 | Contradiction review screenshot. | "But that delay catches risks that autonomous promotion can miss: weak evidence, conflicts, or over-generalized lessons." |
| 0:58-1:18 | Post-approval state. | "The right metric is not only time-to-promotion. It is time saved after avoiding bad reusable knowledge." |
| 1:18-1:32 | Closing card: review where risk compounds. | "PRAXIS uses the human gate where a decision can influence future runs, not for every low-risk AI action." |

## 9. Audit-Trail Accountability Test

**Purpose:** Show that mutations carry actor, timestamp, state history, and evidence.

**Screenshots:** `03-cand1-provenance-confidence.png`, `05-after-confirm-approve.png`, `07-after-keep-this-cand9.png`

| Time | Show on screen | Speak |
|---|---|---|
| 0:00-0:12 | Title card: accountable knowledge mutation. | "This experiment asks whether the team can explain who approved what, when, and why." |
| 0:12-0:36 | Candidate audit trail. | "The candidate starts with pipeline events: distilled and scored, linked to source provenance." |
| 0:36-0:58 | Post-promotion screenshot. | "When a reviewer promotes it, the state transition should be visible and auditable." |
| 0:58-1:18 | Contradiction resolution result. | "The same standard applies to conflict decisions: keep, reject, resolve, or defer should leave a record." |
| 1:18-1:30 | Closing card: governance value. | "For a team or organization, the dashboard is not just UI. It is an accountability layer." |

## 10. Mock vs Live API Decision Safety

**Purpose:** Demonstrate safe rehearsal with mock fixtures and reserve live mutations for disposable data.

**Screenshots:** `02-data-source-dashboard.png`, `04-approval-action.png`, `09-load-eval-data-handoff.png`

| Time | Show on screen | Speak |
|---|---|---|
| 0:00-0:12 | Title card: safe demo source selection. | "This experiment separates rehearsal safety from live mutation testing." |
| 0:12-0:34 | Data-source dashboard screenshot. | "For a stable demo, Monica can use mock fixtures. The UI should make that source clear so the audience knows what is being shown." |
| 0:34-0:58 | Approval action screenshot. | "For live API testing, promotion and rejection must use disposable data only. The dashboard should not accidentally mutate production-like records." |
| 0:58-1:18 | Eval handoff screenshot. | "The same principle applies to eval visibility: show what is configured, and make unavailable states clear." |
| 1:18-1:30 | Closing card: safe by default. | "The pass condition is transparent source state and no risky live mutation during rehearsal." |

## 11. Data-Source Fallback Experiment

**Purpose:** Show resilience and transparency when live data is unavailable.

**Screenshots:** `02-data-source-dashboard.png`, `09-load-eval-data-handoff.png`

| Time | Show on screen | Speak |
|---|---|---|
| 0:00-0:12 | Title card: live unavailable should be obvious. | "This experiment checks how the dashboard behaves when the live API is not available." |
| 0:12-0:36 | Data-source state screenshot. | "The user should see the source state: mock fixture, local API, hosted API, contract version, and configured URL." |
| 0:36-0:58 | Dashboard list or detail state. | "If the app falls back to mock data, that should be explicit. A reviewer should not confuse demo fixtures with live organizational data." |
| 0:58-1:18 | Eval handoff screenshot. | "Eval metrics should follow the same rule: load live evidence when available, or show a clear unavailable state." |
| 1:18-1:30 | Closing card: transparent fallback. | "The pass condition is not just resilience. It is honest resilience." |

## 12. Eval Visibility Experiment

**Purpose:** Show that human approval must connect to measured future outcomes.

**Screenshots:** `09-load-eval-data-handoff.png`, `03-cand1-provenance-confidence.png`

| Time | Show on screen | Speak |
|---|---|---|
| 0:00-0:12 | Title card: approval plus measurement. | "This experiment keeps the dashboard honest: approval alone is not the end of the story." |
| 0:12-0:34 | Candidate detail with approved-knowledge evidence. | "Monica's pillar controls what knowledge can become active. That is the gate." |
| 0:34-0:58 | Eval data screenshot. | "The next question is whether active knowledge improves future runs. The dashboard should expose or link to that eval evidence." |
| 0:58-1:18 | Eval handoff framing. | "This hands cleanly to Dominic's measured proof: corrections, repeated failures, token cost, time, and success rate." |
| 1:18-1:30 | Closing card: measure after promotion. | "The pass condition is visibility into outcomes after knowledge is injected." |

## 13. Cross-Domain Transfer Framing

**Purpose:** Discuss why the PRAXIS loop can generalize beyond coding when evidence, approval, and measured reuse exist.

**Screenshots:** `03-cand1-provenance-confidence.png`, `06-contradictions-review.png`, `09-load-eval-data-handoff.png`

| Time | Show on screen | Speak |
|---|---|---|
| 0:00-0:12 | Title card: same control loop, different domains. | "This is a framing experiment, not a claim that the repo has validated every domain." |
| 0:12-0:34 | Candidate detail with provenance and confidence. | "The pattern can transfer wherever workflows produce logs, candidate lessons, reviewable evidence, and future reuse." |
| 0:34-0:58 | Contradiction review screenshot. | "Research, writing, data, and operations all have the same risk: a bad lesson can compound if no one reviews it." |
| 0:58-1:18 | Eval visibility screenshot. | "The transfer only becomes credible when the future outcome is measured after the approved knowledge is reused." |
| 1:18-1:32 | Closing card: generalize the safeguard, not the claim. | "The honest claim is that PRAXIS provides a reusable safeguard pattern. Each domain still needs its own evidence." |

## 14. Community-Impact Simulation

**Purpose:** Discuss high-impact use cases as simulations unless real participant and outcome data are collected.

**Screenshots:** `03-cand1-provenance-confidence.png`, `06-contradictions-review.png`, `07-after-keep-this-cand9.png`

| Time | Show on screen | Speak |
|---|---|---|
| 0:00-0:12 | Title card: simulation, not deployed public service. | "This final experiment is a community-impact simulation. It is not a claim about real-world outcomes from this repo." |
| 0:12-0:36 | Provenance and confidence screenshot. | "For school services, nonprofit intake, benefits triage, legal-aid routing, or workforce support, the core question is traceability." |
| 0:36-0:58 | Contradiction screenshot. | "If AI suggestions affect people repeatedly, contradictions and weak evidence must be surfaced before reuse." |
| 0:58-1:20 | Human decision result screenshot. | "A human gate can preserve accountability: what was approved, by whom, when, and from what evidence." |
| 1:20-1:34 | Closing card: future research boundary. | "The right capstone claim is a simulation of safeguards, not proof of social impact without real participant data." |

## 15. Poisoned Source Quarantine Test

**Purpose:** Show how poisoned source data is processed by the human gate before it can become active reusable knowledge or harm a future pipeline run.

**Detailed script:** [EXPERIMENT_15_POISONED_SOURCE_QUARANTINE_SCRIPT.md](EXPERIMENT_15_POISONED_SOURCE_QUARANTINE_SCRIPT.md)

**Screenshots:** `02-data-source-dashboard.png`, `03-cand1-provenance-confidence.png`, `04-approval-action.png`, `06-contradictions-review.png`, `08-deferred-contradiction.png`, `09-load-eval-data-handoff.png`, `05-after-confirm-approve.png`

| Time | Show on screen | Speak |
|---|---|---|
| 0:00-0:15 | Title card with the three attack paths. | "This experiment is a poisoned source quarantine test. Poison can enter as data, but it should not become trusted knowledge without human review." |
| 0:15-0:30 | Data source zoom. | "The dashboard makes the source visible before review begins." |
| 0:30-0:45 | Poison payload card. | "The source tries a bad lesson, a contradiction, and an unapproved context sentinel." |
| 0:45-1:15 | Candidate detail and reject action. | "The suspicious candidate stays proposed, exposes provenance and confidence, and can be rejected before activation." |
| 1:15-1:45 | Contradiction pair plus custom/defer controls. | "Contradictory poison is surfaced as a reviewable pair, not silently reused." |
| 1:45-2:15 | Eval sentinel card and eval modal. | "Dominic's eval handoff proves unapproved poison is absent from injected context." |
| 2:15-2:45 | Active safe lesson and team boundary. | "Only safe human-approved knowledge becomes active; Matthew provides candidates, Monica gates them, and Dominic proves impact." |
| 2:45-3:00 | Outcome card. | "The pass condition is quarantine before harm." |

## Production Checklist

- Keep experiments 1-14 under the team presentation cap; Experiment 15 is intentionally planned as a 3-minute composite demo.
- Prefer mock fixtures for stable presentation footage unless the team intentionally uses disposable live API data.
- Keep Monica's narration focused on dashboard, human gate, provenance, confidence, contradictions, audit trail, data-source transparency, and eval handoff.
- Do not claim Matthew's pipeline internals or Dominic's eval proof as Monica-owned work.
- Do not commit API keys, voice IDs, raw voiceover credentials, or generated files that contain secrets.
- If adding ElevenLabs voiceover, use a local environment variable such as `ELEVENLABS_API_KEY`, fetch the voice ID outside source control, and write only the final approved audio/video asset if the team wants it tracked.
