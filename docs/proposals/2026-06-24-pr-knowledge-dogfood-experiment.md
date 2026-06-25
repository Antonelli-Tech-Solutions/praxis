---
date: 2026-06-24
topic: pr-knowledge-dogfood-experiment
---

# Proposal: Dogfood experiment — does past-PR knowledge actually help a coding agent?

**Status**: Open / exploratory · **Raised**: 2026-06-24 · **Source**: brainstorm ·
**Parent**: [2026-06-24-ingest-commits-and-prs.md](2026-06-24-ingest-commits-and-prs.md)

## Summary

Before building any commit/PR ingestion pipeline, run the cheapest experiment that proves (or kills)
the core bet: hand-curate ~10–20 facts from recent merged Praxis PRs, push them directly into a
coding agent's context, and A/B a handful of real Praxis tasks — including one deliberately seeded
footgun — on the existing eval harness. Success is a measurable token/turn reduction **and** a
watched instance of the agent avoiding a footgun it otherwise hits.

## Problem Frame

The parent proposal bets that knowledge from commits/PRs helps coding agents work faster, cheaper,
and better in the repo. As of this writing that value is **illustrative-but-hypothetical** — there is
no observed instance of an agent in the Praxis repo paying for knowledge a past PR already contained.
The example facts in the parent proposal (UMAP `n_neighbors`, Phoenix tracing at import time) are
plausible, not witnessed.

Building the parent proposal's machinery — auto-distillation, the contradiction/supersession currency
angle, two-lane scope-aware retrieval, an auto-supersede write policy — on an unvalidated bet risks
weeks of work on a pipeline that may not pay off. The contradiction/currency angle is the *most*
speculative part: it only earns its keep if agents benefit from these facts at all **and** the repo
churns fast enough that facts go stale mid-usefulness. Neither is established. This experiment
generates the missing evidence for the first of those, cheaply, and lets the result decide whether
the rest gets built.

## Key Decisions

- **Validate before building.** v1 is an experiment, not a pipeline. Everything downstream is gated
  behind its result.
- **Curated + pushed, not extracted + retrieved.** Hand-pick the facts and inject them directly into
  context. This isolates the one unproven claim — *does the knowledge help an agent at all* — from
  extraction quality and retrieval quality. A null result is therefore trustworthy: it means the
  knowledge doesn't help, not that the plumbing failed.
- **Reuse the existing eval harness.** Measurement rides on `knowledge/evals/` and the
  `ClaudeCodeRunner` (real Claude Code sessions), not a new measurement rig.
- **Both signals required for "go."** Quantitative (token/turn reduction) *and* qualitative
  (footgun-avoidance). Either alone is not a green light.
- **Seeded footgun is mandatory.** To *watch* an agent avoid a footgun, at least one task must have a
  footgun documented in a past PR that the agent would plausibly hit blind. Generic tasks can't show
  avoidance.
- **Dogfood scope only.** Praxis-on-Praxis, single-tenant. No tenant-facing surface.

## Requirements

**Fact set**

- R1. Hand-curate ~10–20 facts from recent merged Praxis PRs — high-signal items only (decisions,
  gotchas, conventions, rejected approaches). No auto-distillation.
- R2. Facts are pushed directly into the agent's reachable context for each task. No retrieval, no
  `praxis_get_context` / MCP path in this experiment.

**Task set**

- R3. A small set of representative *real* Praxis coding tasks (a handful, not a suite).
- R4. At least one task is deliberately seeded so that its footgun is documented in a past Praxis PR
  and the agent would plausibly hit it without the curated fact.

**A/B measurement**

- R5. Each task is run both ways — with the curated facts in context, and without — on the existing
  `ClaudeCodeRunner` eval harness.
- R6. Capture token usage and turn/step count per run; compare with-facts vs without-facts.
- R7. Capture a qualitative observation of whether the with-facts run avoids the seeded footgun that
  the without-facts run hits.

**Decision gate**

- R8. **Go** = a measurable token/turn reduction on real tasks **and** observed footgun-avoidance.
  A null result on either signal means the bet is not yet proven — do **not** proceed to the
  ingestion pipeline.

## Success Criteria

- The experiment produces an unambiguous go / no-go on R8, cheap enough (target: ~a day) that a
  no-go is an acceptable outcome rather than sunk cost.
- The token/turn comparison is apples-to-apples (same tasks, same model, facts-in-context the only
  deliberate variable).

## Scope Boundaries

Everything below is **deferred behind this experiment's result** — see the parent proposal:

- Auto-distillation (`CommitIngestor` / `PullRequestIngestor`) — that's the next slice if v1 shows
  signal ([2026-06-24-pr-knowledge-auto-distill-slice.md](2026-06-24-pr-knowledge-auto-distill-slice.md)).
- The contradiction/supersession "currency" angle.
- Two-lane scope-aware retrieval changes to `praxis_get_context`.
- Auto-supersede write policy for code facts.
- Multi-tenant / tenant-facing product surface.
- Incremental ingestion trigger and the GitHub-migration interaction.

## Outstanding Questions

**Resolve before planning**

- What counts as a "measurable" reduction — a threshold (e.g. ≥X% fewer tokens / ≥1 fewer turn), or
  just a clear directional delta the user eyeballs?
- How many tasks, and which ones? (At least one must satisfy R4.)

**Deferred to planning**

- Exactly how facts are pushed into context (system prompt, an injected file, a scratch `CLAUDE.md`,
  etc.) — a planning/implementation detail.
- Agent nondeterminism: how many trials per task/arm are needed for the token/turn delta to be
  credible rather than noise.
