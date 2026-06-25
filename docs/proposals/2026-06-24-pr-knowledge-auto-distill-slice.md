---
date: 2026-06-24
topic: pr-knowledge-auto-distill-slice
---

# Proposal: Thin auto-distill slice — can PR knowledge be extracted and retrieved automatically?

**Status**: Open / exploratory · **Gated on**:
[2026-06-24-pr-knowledge-dogfood-experiment.md](2026-06-24-pr-knowledge-dogfood-experiment.md) showing
signal · **Raised**: 2026-06-24 · **Source**: brainstorm · **Parent**:
[2026-06-24-ingest-commits-and-prs.md](2026-06-24-ingest-commits-and-prs.md)

## Summary

The first build that resembles the parent proposal's real shape: a minimal `CommitIngestor` that
distills facts from merged Praxis PRs with one LLM call each, loads them as `active` facts, and lets
the agent consume them through the real `praxis_get_context` MCP path. It re-runs the dogfood
experiment's task set to test whether *auto-extracted + retrieved* knowledge matches the value of the
*hand-curated + pushed* baseline.

## Problem Frame

The dogfood experiment deliberately removed two variables to isolate the core bet: it hand-curated
the facts (no extraction) and pushed them into context (no retrieval). If it shows signal, two
questions remain before the parent proposal is real:

1. **Extraction** — can an LLM pull facts of comparable value out of a PR automatically, or does the
   hand-curation do most of the work?
2. **Retrieval** — does the existing `praxis_get_context` path actually surface the right fact at the
   right moment, or does the agent never see it?

This slice tests both at once, against the dogfood experiment's known-good baseline. It is the first
point at which the parent proposal's **retrieval gap** (semantic-only retrieval, no file/scope
awareness) can actually bite — and observing it bite is part of the point.

## Key Decisions

- **Gated on the dogfood experiment.** Do not build this until v1
  ([dogfood experiment](2026-06-24-pr-knowledge-dogfood-experiment.md)) shows both signals. If
  curated+pushed facts don't help, auto-distilled+retrieved facts won't either.
- **One LLM call per PR.** A cheap, single-pass distiller — not a tuned multi-step write pipeline.
  Extraction quality is being *measured*, not perfected.
- **Load as `active`, consume via MCP pull.** Facts go straight to `active` (no human gate, acceptable
  in dogfood) and are retrieved through the existing `praxis_get_context` tool unchanged — the
  realistic end-to-end path.
- **PR-primary unit.** Merged PRs (description + review threads) are the reviewed, intentional unit;
  raw commits are secondary.
- **Measure against the baseline, not in a vacuum.** Compare three arms: no-facts, the dogfood
  experiment's curated+pushed, and this slice's auto-distilled+retrieved.

## Requirements

**Extraction**

- R1. Minimal `CommitIngestor` / `PullRequestIngestor` variant alongside `PromptIngestor`. Input = a
  PR (message, body, diff summary, review comments); output = `Insight[]` via one specialized LLM
  distillation call. Source = `git/pr:<n>`.
- R2. The distillation prompt targets durable knowledge (decisions, gotchas, conventions, rejected
  approaches) and ignores churn, renames, and version bumps.
- R3. Backfill the last N merged Praxis PRs through the ingestor.

**Storage & retrieval**

- R4. Distilled facts are written as `active` facts in the graph (reusing the existing write path;
  no contradiction/supersession logic required for the experiment).
- R5. The agent consumes facts through the existing `praxis_get_context` MCP tool. Retrieval is
  **unchanged** — no scope-aware / file-aware enhancements in this slice.

**Measurement**

- R6. Re-run the dogfood experiment's task set (including the seeded-footgun task) and compare the
  auto-distilled+retrieved arm against both the no-facts and curated+pushed arms on token/turn and
  footgun-avoidance.
- R7. Capture two diagnostic signals: extraction quality (signal-to-noise of the distilled facts) and
  retrieval hit rate (did `get_context` surface the relevant fact for each task, especially the
  seeded one?).

## Success Criteria

- The auto-distilled+retrieved arm recovers a meaningful fraction of the curated+pushed arm's
  token/turn and footgun-avoidance benefit.
- If it underperforms, R7 attributes the gap to **extraction** (the distiller missed/garbled the
  fact) vs **retrieval** (the fact existed but `get_context` didn't surface it) — so the next
  increment is chosen on evidence, not guesswork. A retrieval-attributed gap is the concrete
  motivation for the parent proposal's two-lane scope-aware retrieval.

## Scope Boundaries

Still deferred (see the parent proposal):

- The contradiction/supersession "currency" angle — facts are loaded once, not reconciled across the
  timeline.
- Two-lane scope-aware retrieval (`file:` / `module:` / `repo` routing). This slice deliberately runs
  *unchanged* retrieval so any retrieval shortfall is observable and attributable (R7).
- Auto-supersede write policy and the human-gate-vs-auto-supersede question.
- Multi-tenant / tenant-facing product surface.
- Incremental ingestion trigger (post-merge hook / CI) — backfill only for the experiment.

## Outstanding Questions

**Resolve before planning**

- N — how many merged PRs to backfill for a credible test.

**Deferred to planning**

- Diff summarization approach for R1 (full diff is too large to feed raw; how it's condensed).
- Whether the seeded-footgun fact's `scope` needs to be set in a way that helps unchanged retrieval
  find it — and whether failing to find it is itself the finding that justifies the retrieval work.
