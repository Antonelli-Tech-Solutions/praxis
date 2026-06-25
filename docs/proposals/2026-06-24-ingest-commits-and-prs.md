# Proposal: Ingest commits & PRs into Praxis to accelerate coding agents

**Status**: Open / exploratory · **Raised**: 2026-06-24 · **Source**: brainstorm

> This is intentionally high-level. The goal is to get the idea on record, not to spec it. Open
> questions are listed at the end and are expected to stay open for now.

> **Validation path (added 2026-06-24):** the value here is currently hypothetical, so this idea is
> being de-risked in stages rather than built directly.
> [2026-06-24-pr-knowledge-dogfood-experiment.md](2026-06-24-pr-knowledge-dogfood-experiment.md)
> (v1 — *does the knowledge help at all?*, curated + pushed) and
> [2026-06-24-pr-knowledge-auto-distill-slice.md](2026-06-24-pr-knowledge-auto-distill-slice.md)
> (v2 — *can it be auto-extracted and retrieved?*) gate the machinery below behind experimental results.

## Idea in one line

Treat merged PRs and commits as a first-class ingestion **source** so the durable engineering
knowledge they carry — decisions, gotchas, conventions, rejected approaches — becomes retrievable
Praxis facts that help Claude Code (and other coding agents) work **faster** (fewer exploration
turns), **cheaper** (less trial-and-error / file reading), and with **better output** (avoid known
footguns, follow conventions, don't repeat rejected approaches).

## Why Praxis is an unusually good fit

Most "feed git history to an LLM" tools dump commits into a vector store and call it RAG. The
problem is that **code knowledge rots**: a fact extracted today ("clustering uses PCA") is wrong the
moment someone switches to UMAP, and a flat vector store serves both with no way to tell which is
current.

Praxis's claim-conflict + supersession model is built for exactly this. The git timeline is a
**time-ordered stream of claims**. When a newer commit changes something an older fact described,
`ClaimConflictDetector` flags the same subject/attribute slot with an incompatible value, the older
fact is demoted to `rejected` (but retained for provenance), and the newer fact wins. The git
timeline maps directly onto the contradiction/supersession lifecycle. **The differentiator isn't the
extraction — it's keeping the knowledge current as the code evolves.**

Two recent commits make good example facts:

- `d892e88` → "UMAP `n_neighbors` must stay low or topics collapse into a single blob" (tuning /
  gotcha, scoped to clustering).
- `22db05f` → "Phoenix tracing must be set up at app *import* time, not inside `create_app`"
  (footgun, scoped to the serve layer).

An agent touching either area would avoid re-discovering these the hard way.

## What's worth extracting (ranked by signal, not volume)

Distilling *every* commit is the trap — ~80% is mechanical churn (renames, version bumps,
formatting) that pollutes retrieval. Extract only durable, reusable knowledge, roughly in this
priority:

1. **Rejected approaches / reverts** (highest signal). A commit that reverts or fixes a recent one
   teaches "X doesn't work because Y." Ingest these *as contradictions* against the naive approach.
2. **PR review threads.** Where senior→junior knowledge transfer actually happens, and invisible to
   anyone reading only commit messages.
3. **Decision / rationale facts** — the "why," especially when it references an FR (`FR-005`, …);
   bonus opportunity to cross-link to the spec-kit requirement.
4. **Gotchas / footguns** — from fix commits and CI-failure fixes.
5. **Conventions** — commits that establish a repeated pattern.

Deliberately *not* extracted: "where things live" architecture facts from diffs — they drift fastest
and the codebase already covers structure.

## How it plugs in (small surface area)

Reuses almost everything in the existing write pipeline.

- New ingestor variant alongside `PromptIngestor`: `CommitIngestor` / `PullRequestIngestor`. Takes
  (message, diff summary, PR body, review comments) → emits `Insight[]` with
  `source = "git/pr:<n>"` or `"git/commit:<sha>"`, a `scope` chosen by the distiller (see below),
  and `category = decision|gotcha|convention|rejected`.
- A specialized distillation prompt (not the generic `SPLIT_PROMPT`): extract durable engineering
  knowledge; ignore churn, renames, version bumps.

**Provenance is not scope.** The file paths in a diff are *provenance* — every fact records which
commit/files it came from, for free, for verifiability. Where a fact *applies* is a separate
judgment the distiller must make and write into `scope`. A revert in `clustering.py` might teach a
file-local lesson *or* a global one ("never tune UMAP by raising `n_neighbors`"); that can't be
derived mechanically from the diff's file list. Not every fact is file-aware — scope lands in one of
roughly three tiers, with a small vocabulary to make routing concrete:

- `file:<path>` — anchored to a specific file/symbol (most gotchas, tuning rationale).
- `module:<name>` — a coherent subsystem spanning several files (e.g. "the write pipeline embeds
  text exactly once," "contradiction edges are never deleted").
- `repo` — global conventions with no file anchor ("eval cases use base-name=after, `_before`=control,"
  "redact PII before storage").
- Downstream is unchanged: claim extraction, conflict detection, contradiction edges, human gate,
  embedding. Provenance + audit trail give fact→sha verifiability for free.

**Unit:** PR-primary, commit-secondary. A merged PR is the reviewed, intentional unit and carries
description + review threads; raw commits matter mainly for revert/fix detection.

## The gap to flag early: retrieval must be scope-aware (not just file-aware)

Extraction is worthless if the gotcha doesn't surface at the right moment. Retrieval today is pure
semantic similarity over a query string. But the natural trigger for a coding agent is "I'm about to
edit `clustering.py`" — you want the n_neighbors fact surfaced by **file scope**, not by hoping the
task text is semantically near it.

The trap is making file-scope a hard *filter*. Conventions and module-level facts (`repo` /
`module:` scope) have no file anchor; if file-awareness gates retrieval, a convention born in one
file would never surface anywhere else — exactly backwards. So retrieval runs **two lanes**:

- **Scoped lane** — facts whose `scope` matches the files I'm touching, *boosted* (not exclusive).
- **Global lane** — `repo`-scoped (and semantically relevant `module:`) facts, competing on plain
  similarity to the task, or even always-on candidates.

The union feeds the model. Concretely this means a retrieval enhancement: scope-routing in
`get_context`, or a new `praxis_get_context_for_files([...])` affordance that takes the active file
set. It shapes what scope metadata the ingestor must attach, so it's worth deciding early.

## Open questions

1. **Human-gate vs. auto-supersede for code facts.** Facts derived from already-reviewed, merged PRs
   arguably don't need a second human gate — a recency-wins auto-supersede policy may fit better than
   the session-ingestion proposed→active gate. Likely a distinct write policy.
2. **Backfill vs. incremental, and where the trigger lives.** Seed with the last N merged PRs, then
   ingest each new merge. The incremental trigger interacts with the GitHub migration.
3. **Noise-filter aggressiveness.** PR-descriptions-and-reviews-only (high precision, cheap) vs. also
   distilling diffs (higher recall, noisier, more expensive).
4. **Retrieval trigger.** How the scoped + global two-lane surfacing actually works in the MCP layer
   (see gap above) — including the boost weighting and whether `repo` facts are always-on.
5. **Cross-linking to specs.** Whether/how to tie commit-derived facts to the FRs they reference.
