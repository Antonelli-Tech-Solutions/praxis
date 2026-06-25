---
date: 2026-06-24
updated: 2026-06-24
topic: pr-knowledge-auto-distill-slice
---

# Proposal: Thin auto-distill slice — can PR knowledge be extracted and retrieved automatically?

**Status**: Open / exploratory · **Gated on**: an *iterated* dogfood re-run showing the dual signal on
a validity-gated footgun (v1 is now **built and run** — see below) · **Raised**: 2026-06-24 ·
**Source**: brainstorm · **Parent**:
[2026-06-24-ingest-commits-and-prs.md](2026-06-24-ingest-commits-and-prs.md)

> **Updated 2026-06-24 after v1 was implemented.** The dogfood experiment
> ([proposal](2026-06-24-pr-knowledge-dogfood-experiment.md)) is no longer hypothetical: the apparatus
> exists at [`knowledge/evals/cases/dom/pr_knowledge_dogfood/`](../../knowledge/evals/cases/dom/pr_knowledge_dogfood/)
> and has run for real. This slice no longer assumes a clean-room build — it **reuses** that apparatus
> (curated-fact format, paired-case convention, the trial/aggregation/go-gate tooling, the proven
> footgun template) and inherits its lessons. See *Now built (v1)* below.

## Summary

The first build that resembles the parent proposal's real shape: a minimal `CommitIngestor` that
distills facts from merged Praxis PRs with one LLM call each, loads them as `active` facts, and lets
the agent consume them through the real `praxis_get_context` MCP path. It reuses the dogfood
experiment's **already-built** task set, paired-case convention, and aggregation tooling to test
whether *auto-extracted + retrieved* knowledge matches the value of the *hand-curated + pushed*
baseline that v1 produced.

## Problem Frame

The dogfood experiment deliberately removed two variables to isolate the core bet: it hand-curated
the facts (no extraction) and pushed them into context (no retrieval). If it shows signal, two
questions remain before the parent proposal is real:

1. **Extraction** — can an LLM pull facts of comparable value out of a PR automatically, or does the
   hand-curation do most of the work?
2. **Retrieval** — does the existing `praxis_get_context` path actually surface the right fact at the
   right moment, or does the agent never see it?

This slice tests both at once, against the dogfood experiment's baseline. It is the first
point at which the parent proposal's **retrieval gap** (semantic-only retrieval, no file/scope
awareness) can actually bite — and observing it bite is part of the point.

## Now built (v1 → v2) — what this slice reuses and what the experiments found

The dogfood experiment has been implemented and run twice. Concrete, reusable artifacts now exist under
[`knowledge/evals/cases/dom/pr_knowledge_dogfood/`](../../knowledge/evals/cases/dom/pr_knowledge_dogfood/):

- **Curated-fact format + provenance** (`facts.md`): ~13 facts, each one or two sentences, traced to a
  real merged PR/commit. This is the exact shape `CommitIngestor` output must match to drop into the
  same seeding path — the auto-distilled facts replace `facts.md` as the seed source.
- **Paired-case convention** (`<task>/` treatment + `<task>_before/` control). Treatment carries the
  facts via `seeded_insight.direct_to_graph` (written `active`); the control is empty. **Controls use a
  positive-assertion shape** (assert the footgun is *present*) rather than `xfail` — an `xfail` control
  silently XPASSes when agent nondeterminism dodges the footgun, reading as a false win. Reuse this shape.
- **Cost-to-correct trial/aggregation/go-gate tooling** (`analyze.py`, with offline fixture-backed
  tests). Runs each task's treatment + control + a rework turn (control's wrong output re-prompted with
  the fact as review feedback) in-process through the real `ClaudeCodeRunner` (not the CLI — that
  clobbers `results/baseline.jsonl`), and gates on `cost_usd` cost-to-correct + footgun-flips. Adding
  this slice's **third arm** (auto-distilled + retrieved) is a natural extension of this code, not new
  scaffolding.
- **A validated footgun template** (`yoyo_lazy_import`, from `1fdb8be`): a create-task whose blind
  default — a top-level `from knowledge...` import in a yoyo migration — reliably trips a documented
  gotcha (yoyo execs with the repo root off `sys.path`), graded by a column-0-import regex. v2 showed
  its control exhibits the footgun 3/3; this is the template a credible seeded footgun should follow.
  (`umap_neighbors` is also a footgun but proved variance-prone — control-exhibit 2/3 in v1, 0/3 in v2
  — so it is demoted to a non-gating cost signal.)

**v1's verdict was a strict NO-GO — but apparatus-attributed, not "knowledge doesn't help"** (full
diagnosis in the suite's `RESULTS.md`):

- On the one *valid, blind-tempting* footgun (`umap_neighbors`) curated knowledge produced a clean
  **dual-signal win**: the treatment avoided the footgun every trial while the control mostly hit it,
  **and** the control burned ~2.3× the output tokens flailing without the fact.
- The gate failed because two of three task constructs were weak: one footgun (`phoenix_tracing`) was
  *not* blind-tempting (the control never hit it, so nothing to flip), and the convention task measured
  output correctness, not cost.
- **Cost-metric lesson:** in the sealed box (no repo, Bash/web disallowed) there is little exploration
  to shortcut, so raw token *volume* is the wrong primary cost signal — and it **understates** the
  control, which pays an unmeasured rework tail to fix wrong output. Prefer `cost_usd`, `num_turns`,
  footgun-flips, and a **cost-to-correct** comparison (control first-pass + rework vs. treatment).

**v2 ran the iteration** (replaced the invalid footgun with `yoyo_lazy_import`, added a repo-mounted
task, re-gated on cost-to-correct). Result: still a strict NO-GO, but the bet is **better-supported** —
a *valid* footgun (`yoyo`) flipped cleanly **and** cost-to-correct favored knowledge on 3/4 tasks. The
two remaining gaps are apparatus, not knowledge value: `umap`'s footgun is too variance-prone to gate
on, and the single-file repo-mounted task didn't surface the exploration-savings lever.

**Implication for this slice:** the cost-to-correct metric and the curated-fact value are now
validated; what's missing for a clean GO is footgun-construct *robustness* (≥2 reliably-blind-tempting
footguns, not one) and a heavier repo-mounted task. Add those to the dogfood suite first; once the gate
is clean-green, this slice's only new variable is auto-distillation + retrieval — everything else is
reused.

## Key Decisions

- **Gated on a clean-green dogfood gate.** v2 ran the iteration and got partway: a valid footgun
  (`yoyo`) flipped and cost-to-correct favored knowledge on 3/4 tasks, but the strict gate is still
  NO-GO (one valid footgun + a null repo task). Do not stand up the auto-distilled arm until the dogfood
  suite gate is clean-green (≥2 reliably-blind-tempting footguns + a repo-mounted task that shows the
  exploration-savings lever). If curated+pushed facts can't clear that bar, auto-distilled+retrieved
  facts won't.
- **One LLM call per PR.** A cheap, single-pass distiller — not a tuned multi-step write pipeline.
  Extraction quality is being *measured*, not perfected.
- **Load as `active`, consume via MCP pull.** Facts go straight to `active` (no human gate, acceptable
  in dogfood) and are retrieved through the existing `praxis_get_context` tool unchanged — the
  realistic end-to-end path.
- **PR-primary unit.** Merged PRs (description + review threads) are the reviewed, intentional unit;
  raw commits are secondary.
- **Measure against the baseline, not in a vacuum.** Compare three arms: no-facts, the dogfood
  experiment's curated+pushed (now an *existing* baseline in the suite's `RESULTS.data.json`), and this
  slice's auto-distilled+retrieved — by extending the existing `analyze.py` aggregator with a third arm.
- **Use v1's cost metric, not raw token volume.** Score on `cost_usd` / `num_turns` / footgun-flips and
  a cost-to-correct comparison (per the v1 lesson), and reuse v1's validity discipline: confirm each
  control actually exhibits the footgun before trusting a treatment's avoidance.

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

- R6. Reuse the dogfood suite's task set + paired-case convention (validity-gated footguns) and extend
  its `analyze.py` with a third arm, comparing auto-distilled+retrieved against the no-facts and
  curated+pushed arms on `cost_usd` / `num_turns` / footgun-flips and cost-to-correct (not raw token
  volume).
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

- ~~N — how many merged PRs to backfill.~~ Provisionally **~30** (carried in the
  [auto-distill plan](../plans/2026-06-24-002-feat-pr-knowledge-auto-distill-plan.md)); revisit if the
  iterated v1 task set grows.
- Iterate v1 first, or fold v1's iteration into this slice? The apparatus is shared, so a second
  validity-gated footgun + repo-mounted task + cost-to-correct metric could land either as a v1 re-run
  or as this slice's no-facts/curated arms. Decide before planning so the work isn't done twice.

**Deferred to planning**

- Diff summarization approach for R1 (full diff is too large to feed raw; how it's condensed).
- Whether the seeded-footgun fact's `scope` needs to be set in a way that helps unchanged retrieval
  find it — and whether failing to find it is itself the finding that justifies the retrieval work.
  (v1 ran the whole-file reader, so retrieval was never exercised — this slice is the first to test it.)
