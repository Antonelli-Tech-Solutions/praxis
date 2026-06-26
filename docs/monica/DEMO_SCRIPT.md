# PRAXIS Human Gate - Recorded Demo Narration Script

**Owner:** Monica Peters
**Updated:** 2026-06-25
**Purpose:** speaking script for the generated Monica experiment demo videos.
**Source script:** [EXPERIMENTS_VIDEO_SCRIPTS.md](EXPERIMENTS_VIDEO_SCRIPTS.md)
**Generated videos:** [experiment-video-capture-2026-06-25](videos/experiment-video-capture-2026-06-25/)

Use this file when presenting over the silent captioned MP4s in
`docs/monica/videos/experiment-video-capture-2026-06-25/`. The videos already
show the screen flow and zoom into the relevant dashboard area; this file is the
spoken narration to read live or record as voiceover.

## Presentation Framing

> "My capstone pillar is the PRAXIS human gate: the review layer that decides
> which AI-learned lessons are trustworthy enough to become reusable knowledge.
> These short experiments show provenance, confidence, approval, contradiction
> handling, auditability, source transparency, and the handoff to eval proof."

Keep each narration aligned to the matching MP4. Experiments 2-14 are designed
to stay well under the 2 minutes 50 seconds presentation cap; Experiment 15 is
a 3-minute composite poison-quarantine demo.

## Video Playlist

| # | Video | Length |
|---|---|---:|
| 1 | [experiment-01-cold-vs-knowledge-injected-agent-run.mp4](videos/experiment-video-capture-2026-06-25/experiment-01-cold-vs-knowledge-injected-agent-run.mp4) | 55s |
| 2 | [experiment-02-autonomous-memory-vs-human-gated-knowledge.mp4](videos/experiment-video-capture-2026-06-25/experiment-02-autonomous-memory-vs-human-gated-knowledge.mp4) | 75s |
| 3 | [experiment-03-proposed-only-vs-active-only-injection.mp4](videos/experiment-video-capture-2026-06-25/experiment-03-proposed-only-vs-active-only-injection.mp4) | 75s |
| 4 | [experiment-04-low-confidence-promotion-test.mp4](videos/experiment-video-capture-2026-06-25/experiment-04-low-confidence-promotion-test.mp4) | 75s |
| 5 | [experiment-05-contradiction-resolution-test.mp4](videos/experiment-video-capture-2026-06-25/experiment-05-contradiction-resolution-test.mp4) | 75s |
| 6 | [experiment-06-provenance-trust-test.mp4](videos/experiment-video-capture-2026-06-25/experiment-06-provenance-trust-test.mp4) | 75s |
| 7 | [experiment-07-confidence-breakdown-test.mp4](videos/experiment-video-capture-2026-06-25/experiment-07-confidence-breakdown-test.mp4) | 90s |
| 8 | [experiment-08-human-gate-latency-vs-safety-tradeoff.mp4](videos/experiment-video-capture-2026-06-25/experiment-08-human-gate-latency-vs-safety-tradeoff.mp4) | 75s |
| 9 | [experiment-09-audit-trail-accountability-test.mp4](videos/experiment-video-capture-2026-06-25/experiment-09-audit-trail-accountability-test.mp4) | 75s |
| 10 | [experiment-10-mock-vs-live-api-decision-safety.mp4](videos/experiment-video-capture-2026-06-25/experiment-10-mock-vs-live-api-decision-safety.mp4) | 75s |
| 11 | [experiment-11-data-source-fallback-experiment.mp4](videos/experiment-video-capture-2026-06-25/experiment-11-data-source-fallback-experiment.mp4) | 75s |
| 12 | [experiment-12-eval-visibility-experiment.mp4](videos/experiment-video-capture-2026-06-25/experiment-12-eval-visibility-experiment.mp4) | 75s |
| 13 | [experiment-13-cross-domain-transfer-framing.mp4](videos/experiment-video-capture-2026-06-25/experiment-13-cross-domain-transfer-framing.mp4) | 75s |
| 14 | [experiment-14-community-impact-simulation.mp4](videos/experiment-video-capture-2026-06-25/experiment-14-community-impact-simulation.mp4) | 75s |
| 15 | [experiment-15-poisoned-source-quarantine-test.mp4](videos/experiment-video-capture-2026-06-25/experiment-15-poisoned-source-quarantine-test.mp4) | 180s |

## Experiment 01 - Cold vs Knowledge-Injected Agent Run

**Video:** [experiment-01-cold-vs-knowledge-injected-agent-run.mp4](videos/experiment-video-capture-2026-06-25/experiment-01-cold-vs-knowledge-injected-agent-run.mp4)
**Length:** 55 seconds

| Time | Speak |
|---|---|
| 0:00-0:10 | "This experiment asks whether PRAXIS makes an agent measurably better after a human-approved lesson is available." |
| 0:10-0:22 | "The cold run starts without PRAXIS context. The knowledge-injected run receives only active, approved knowledge, not raw memory or unreviewed suggestions." |
| 0:22-0:34 | "Before reuse, the reviewer can inspect the original log line, confidence score, and audit trail behind the lesson." |
| 0:34-0:46 | "The expected improvement is fewer repeated corrections, less wasted time, and no drop in the success standard." |
| 0:46-0:55 | "Monica's dashboard controls what may enter context. Dominic's eval layer proves whether that approved knowledge improves the next run." |

## Experiment 02 - Autonomous Memory vs Human-Gated Knowledge

**Video:** [experiment-02-autonomous-memory-vs-human-gated-knowledge.mp4](videos/experiment-video-capture-2026-06-25/experiment-02-autonomous-memory-vs-human-gated-knowledge.mp4)
**Length:** 75 seconds

| Time | Speak |
|---|---|
| 0:00-0:15 | "This experiment compares automatic memory promotion with the PRAXIS human-gated knowledge flow." |
| 0:15-0:30 | "Autonomous memory can save a plausible lesson quickly, but speed is not the same as trust. A wrong lesson can be reused again and again." |
| 0:30-0:45 | "In the gated path, the reviewer sees the candidate, confidence, evidence, and state before the lesson becomes active." |
| 0:45-1:00 | "When the system finds a conflict, it surfaces the decision instead of burying a contradiction inside memory." |
| 1:00-1:15 | "The point is not to slow every AI action. The point is to gate reusable knowledge before a bad lesson compounds." |

## Experiment 03 - Proposed-Only vs Active-Only Injection

**Video:** [experiment-03-proposed-only-vs-active-only-injection.mp4](videos/experiment-video-capture-2026-06-25/experiment-03-proposed-only-vs-active-only-injection.mp4)
**Length:** 75 seconds

| Time | Speak |
|---|---|
| 0:00-0:15 | "This experiment protects the core lifecycle rule: proposed knowledge is staged, and active knowledge is reusable." |
| 0:15-0:30 | "A proposed candidate can be inspected, challenged, rejected, or approved, but it should not influence future agent context yet." |
| 0:30-0:45 | "The state change happens only when a reviewer explicitly confirms the promotion." |
| 0:45-1:00 | "After approval, the lesson becomes active and eligible for future context injection." |
| 1:00-1:15 | "The experiment passes when proposed-only injection is blocked and active-only injection is allowed." |

## Experiment 04 - Low-Confidence Promotion Test

**Video:** [experiment-04-low-confidence-promotion-test.mp4](videos/experiment-video-capture-2026-06-25/experiment-04-low-confidence-promotion-test.mp4)
**Length:** 75 seconds

| Time | Speak |
|---|---|
| 0:00-0:15 | "This experiment focuses on weak evidence: cases where a lesson exists, but the score is not strong enough to trust automatically." |
| 0:15-0:30 | "The reviewer should see why the score is low or mixed. Frequency, recency, and breadth need to be open to inspection." |
| 0:30-0:45 | "If the reviewer still promotes the candidate, that action should be deliberate, confirmed, and auditable." |
| 0:45-1:00 | "The dashboard should not hide uncertainty. It should make the risk visible before promotion." |
| 1:00-1:15 | "Confidence is a warning signal, not an invisible auto-promotion rule. Weak evidence should never silently become organizational memory." |

## Experiment 05 - Contradiction-Resolution Test

**Video:** [experiment-05-contradiction-resolution-test.mp4](videos/experiment-video-capture-2026-06-25/experiment-05-contradiction-resolution-test.mp4)
**Length:** 75 seconds

| Time | Speak |
|---|---|
| 0:00-0:15 | "This experiment shows how PRAXIS handles two lessons that cannot both be universally true." |
| 0:15-0:30 | "The dashboard presents the conflict as a pair. One lesson may be stronger, newer, or better supported than the rival." |
| 0:30-0:45 | "A reviewer can keep one lesson, reject the other, or write a custom resolution when neither side is complete." |
| 0:45-1:00 | "If the evidence is not strong enough, deferral is better than forcing a bad decision." |
| 1:00-1:15 | "The pass condition is simple: contradictions must be visible before they are reused." |

## Experiment 06 - Provenance Trust Test

**Video:** [experiment-06-provenance-trust-test.mp4](videos/experiment-video-capture-2026-06-25/experiment-06-provenance-trust-test.mp4)
**Length:** 75 seconds

| Time | Speak |
|---|---|
| 0:00-0:15 | "This experiment compares a lesson shown by itself against a lesson shown with source provenance." |
| 0:15-0:30 | "The Monica contract includes provenance on each candidate, including the log file and line where the evidence came from." |
| 0:30-0:45 | "That changes the review from trusting advice to checking evidence. The reviewer can trace what the pipeline distilled and scored." |
| 0:45-1:00 | "The data source matters too. Reviewers should know whether they are looking at mock fixtures, a local API, or hosted data." |
| 1:00-1:15 | "A candidate without evidence is just advice. A candidate with provenance can be reviewed." |

## Experiment 07 - Confidence-Breakdown Test

**Video:** [experiment-07-confidence-breakdown-test.mp4](videos/experiment-video-capture-2026-06-25/experiment-07-confidence-breakdown-test.mp4)
**Length:** 90 seconds

| Time | Speak |
|---|---|
| 0:00-0:15 | "This experiment replaces a black-box confidence number with an inspectable score." |
| 0:15-0:35 | "The reviewer can challenge the components. Was the lesson frequent enough? Was it recent? Did it apply across enough workflows?" |
| 0:35-0:50 | "That matters because approval turns a candidate into reusable context. The reviewer should understand the score before acting." |
| 0:50-1:05 | "When the action is taken, it becomes part of the candidate's history, not an invisible mutation." |
| 1:05-1:20 | "The dashboard does not ask for blind trust in a number. It gives reviewers the pieces behind the number." |
| 1:20-1:30 | "The pass condition is that the reviewer can explain the confidence score before approving or rejecting the lesson." |

## Experiment 08 - Human-Gate Latency vs Safety Tradeoff

**Video:** [experiment-08-human-gate-latency-vs-safety-tradeoff.mp4](videos/experiment-video-capture-2026-06-25/experiment-08-human-gate-latency-vs-safety-tradeoff.mp4)
**Length:** 75 seconds

| Time | Speak |
|---|---|
| 0:00-0:15 | "This experiment frames the tradeoff between instant promotion and slower human review." |
| 0:15-0:30 | "The human gate adds latency. A reviewer has to inspect the evidence and confirm the action." |
| 0:30-0:45 | "But that delay catches risks that automatic promotion can miss: weak evidence, contradictions, or over-generalized lessons." |
| 0:45-1:00 | "The right metric is not only time-to-promotion. It is time saved by avoiding bad reusable knowledge." |
| 1:00-1:15 | "PRAXIS uses the human gate where risk compounds across future runs, not for every low-risk AI action." |

## Experiment 09 - Audit-Trail Accountability Test

**Video:** [experiment-09-audit-trail-accountability-test.mp4](videos/experiment-video-capture-2026-06-25/experiment-09-audit-trail-accountability-test.mp4)
**Length:** 75 seconds

| Time | Speak |
|---|---|
| 0:00-0:15 | "This experiment asks whether the team can explain who approved what, when, and why." |
| 0:15-0:30 | "A candidate starts with pipeline history: distilled and scored events linked back to source provenance." |
| 0:30-0:45 | "When a reviewer promotes it, the state transition should be visible and explainable later." |
| 0:45-1:00 | "The same standard applies to contradiction handling. Keep, reject, resolve, or defer should leave a record." |
| 1:00-1:15 | "For a team or organization, the dashboard is not just UI. It is an accountability layer." |

## Experiment 10 - Mock vs Live API Decision Safety

**Video:** [experiment-10-mock-vs-live-api-decision-safety.mp4](videos/experiment-video-capture-2026-06-25/experiment-10-mock-vs-live-api-decision-safety.mp4)
**Length:** 75 seconds

| Time | Speak |
|---|---|
| 0:00-0:15 | "This experiment separates stable rehearsal from live mutation testing." |
| 0:15-0:30 | "For a predictable demo, Monica can use mock fixtures. The dashboard should make that source obvious to the audience." |
| 0:30-0:45 | "For live API testing, promotion and rejection should use disposable records only, not production-like knowledge." |
| 0:45-1:00 | "The same principle applies to eval visibility. The UI should show what is configured and what is unavailable." |
| 1:00-1:15 | "The pass condition is transparent source state and no risky live mutation during rehearsal." |

## Experiment 11 - Data-Source Fallback Experiment

**Video:** [experiment-11-data-source-fallback-experiment.mp4](videos/experiment-video-capture-2026-06-25/experiment-11-data-source-fallback-experiment.mp4)
**Length:** 75 seconds

| Time | Speak |
|---|---|
| 0:00-0:15 | "This experiment checks what happens when live data is unavailable." |
| 0:15-0:30 | "The user should see the source state: mock fixture, local API, hosted API, contract version, and configured URL." |
| 0:30-0:45 | "If the app falls back to mock data, that fallback should be explicit." |
| 0:45-1:00 | "A reviewer should not confuse demo fixtures with live organizational knowledge, especially before approving or rejecting candidates." |
| 1:00-1:15 | "The pass condition is not just resilience. It is honest resilience." |

## Experiment 12 - Eval Visibility Experiment

**Video:** [experiment-12-eval-visibility-experiment.mp4](videos/experiment-video-capture-2026-06-25/experiment-12-eval-visibility-experiment.mp4)
**Length:** 75 seconds

| Time | Speak |
|---|---|
| 0:00-0:15 | "This experiment keeps the dashboard honest: approval alone is not the end of the story." |
| 0:15-0:30 | "Monica's pillar controls which lessons become active. That is the gate." |
| 0:30-0:45 | "The next question is whether active knowledge improves future runs, so the dashboard should expose or link to eval evidence." |
| 0:45-1:00 | "That handoff belongs with measured proof: corrections, repeated failures, token cost, time, and success rate." |
| 1:00-1:15 | "The pass condition is visibility into what happened after approved knowledge was injected." |

## Experiment 13 - Cross-Domain Transfer Framing

**Video:** [experiment-13-cross-domain-transfer-framing.mp4](videos/experiment-video-capture-2026-06-25/experiment-13-cross-domain-transfer-framing.mp4)
**Length:** 75 seconds

| Time | Speak |
|---|---|
| 0:00-0:15 | "This is a framing experiment, not a claim that this repo has validated every domain." |
| 0:15-0:30 | "The pattern can transfer wherever workflows produce logs, candidate lessons, reviewable evidence, and future reuse." |
| 0:30-0:45 | "Research, writing, data, and operations all share the same risk: a bad lesson can compound if no one reviews it." |
| 0:45-1:00 | "The transfer only becomes credible when future outcomes are measured after approved knowledge is reused." |
| 1:00-1:15 | "The honest claim is that PRAXIS provides a reusable safeguard pattern. Each domain still needs its own evidence." |

## Experiment 14 - Community-Impact Simulation

**Video:** [experiment-14-community-impact-simulation.mp4](videos/experiment-video-capture-2026-06-25/experiment-14-community-impact-simulation.mp4)
**Length:** 75 seconds

| Time | Speak |
|---|---|
| 0:00-0:15 | "This final experiment is a community-impact simulation. It is not a claim about real-world outcomes from this repo." |
| 0:15-0:30 | "For school services, nonprofit intake, benefits triage, legal-aid routing, or workforce support, the core question is traceability." |
| 0:30-0:45 | "If AI suggestions affect people repeatedly, contradictions and weak evidence must be surfaced before reuse." |
| 0:45-1:00 | "A human gate can preserve accountability: what was approved, by whom, when, and from what evidence." |
| 1:00-1:15 | "The right capstone claim is a simulation of safeguards, not proof of social impact without real participant data." |

## Experiment 15 - Poisoned Source Quarantine Test

**Video:** [experiment-15-poisoned-source-quarantine-test.mp4](videos/experiment-video-capture-2026-06-25/experiment-15-poisoned-source-quarantine-test.mp4)
**Length:** 180 seconds
**Detailed script:** [EXPERIMENT_15_POISONED_SOURCE_QUARANTINE_SCRIPT.md](EXPERIMENT_15_POISONED_SOURCE_QUARANTINE_SCRIPT.md)

| Time | Speak |
|---|---|
| 0:00-0:15 | "This experiment is a poisoned source quarantine test. The point is simple: poison can enter as data, but it should not become trusted knowledge without human review." |
| 0:15-0:30 | "First, the dashboard makes the source visible. Reviewers should know whether candidates came from mock fixtures, local API data, or a live service." |
| 0:30-0:45 | "The poisoned source tries three attacks: a bad lesson, a contradiction against trusted guidance, and an unapproved sentinel trying to reach future context." |
| 0:45-1:00 | "Attack one becomes a proposed candidate, not active knowledge. The reviewer can inspect provenance, confidence, content, and history before taking action." |
| 1:00-1:15 | "The safe response is quarantine. The reviewer rejects the bad lesson instead of approving it into reusable context." |
| 1:15-1:30 | "Attack two is a contradictory poison attempt. PRAXIS shows both sides together instead of silently letting a bad memory override a trusted one." |
| 1:30-1:45 | "If neither side is fully safe, the reviewer can write a custom resolution or defer. A forced decision is not required." |
| 1:45-2:00 | "Attack three is the most important safety property: unapproved poison must not appear in future injected context." |
| 2:00-2:15 | "This is the handoff to Dominic's eval proof. The dashboard can show or link the evidence that the gate worked after review." |
| 2:15-2:30 | "Only safe, human-approved knowledge should become active. Rejected or proposed poison remains outside reusable context." |
| 2:30-2:45 | "Matthew supplies candidate generation and persistence, Monica gates the candidate in the frontend, and Dominic proves future-run impact." |
| 2:45-3:00 | "The pass condition is quarantine before harm: bad candidates are rejected, conflicts are surfaced, and unapproved poison is forbidden from injected context." |

## Closing Line

> "My contribution is the review surface that makes PRAXIS auditable:
> provenance on every lesson, confidence reviewers can inspect, contradictions
> that surface before reuse, and promotions that humans control."

## Voiceover And Safety Notes

- Do not store text-to-speech API keys, voice IDs, or raw credentials in this repository.
- If ElevenLabs voiceover is added, use a local environment variable such as `ELEVENLABS_API_KEY`.
- Keep generated raw audio outside source control unless the team explicitly decides to track final approved assets.
- Prefer mock fixtures for rehearsal unless the team intentionally uses disposable live API data.
- Do not claim Matthew's pipeline internals or Dominic's eval proof as Monica-owned work.
