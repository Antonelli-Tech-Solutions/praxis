---
date: 2026-06-25
updated: 2026-06-25
topic: ce-compound-praxis-ingestion-bridge
---

# Proposal: Bridge `/ce-compound` into Praxis as a session ingestion source

**Status**: Open / exploratory · **Gated on**: the dogfood retrieval gate going clean-green
(read side) — write side can start sooner · **Raised**: 2026-06-25 · **Source**: brainstorm ·
**Sibling**: [2026-06-24-ingest-commits-and-prs.md](2026-06-24-ingest-commits-and-prs.md),
[2026-06-24-pr-knowledge-auto-distill-slice.md](2026-06-24-pr-knowledge-auto-distill-slice.md)

## Idea in one line

`/ce-compound` and the [`CommitIngestor`](../../knowledge/injestion/injestor_variants/commit_injestor.py)
are the **same extractor reached from two triggers** — session-end (human-in-loop) vs. post-merge
(async). Make ce-compound a third ingestion *source* into Praxis's candidate lifecycle instead of a
parallel flat-file knowledge store, so the repo dogfoods its own product on the knowledge it
generates about itself.

## Problem frame

`/ce-compound` is Praxis rebuilt as a markdown convention. It captures a solved problem at session
end and writes a structured doc to `docs/solutions/`. Praxis captures durable lessons, gates them
through review, dedups/reconciles them in a graph, and makes them retrievable. Same loop, two
maturity levels:

| | `/ce-compound` | Praxis |
|---|---|---|
| Capture | session-end, human-in-loop | session-end (this proposal) *or* async PR distill |
| Store | flat markdown in `docs/solutions/` | graph-backed facts (pgvector) |
| Dedup / conflict | none | merge on near-dup, supersede on conflict |
| Governance | in-chat "is this right?" | `proposed → suggested → active` + dashboard gate |
| Recall | agent must `grep` | semantic `praxis_get_context` |
| Proof | none | eval harness (cold vs. injected) |

Two facts make this concrete rather than academic:

1. **`docs/solutions/` is empty in this repo.** The convention is declared in `CLAUDE.md` but nothing
   has ever been written. "Replace" has nothing to lose; "augment" has nothing to migrate.
2. **The extractor already exists.** `CommitIngestor` distills a unit into typed `Insight[]` with one
   structured LLM call and writes each through `Ingestor.ingest(..., state="proposed")` — straight
   into the candidate lifecycle. ce-compound needs the *same* extractor with a session-shaped input
   and prompt; it does not need new write machinery.

The risk of doing nothing principled: **two stores that drift.** A flat-file lesson and a graph fact
covering the same gotcha will diverge, and there is no dedup/conflict policy across the boundary.
Pick one system of record.

## Why route through the candidate lifecycle, not the MCP shortcut

The obvious shortcut is `praxis_add_insight` from the [MCP server](../matt/MCP_SERVER.md). It works,
but it is the wrong pipe for ce-compound output, for three reasons:

1. **It bypasses governance.** `add_insight` treats the in-chat confirmation as the human gate and
   lands the fact `active` at `confidence = 1.0`. That skips the `proposed → suggested → active`
   lifecycle and the dashboard review — which is Praxis's headline differentiator over "memory."
   Routing ce-compound through `Ingestor.ingest(state="proposed")` instead means self-captured
   knowledge is *reviewable*, dedup'd, and reconciled like every other candidate. **Dogfooding the
   gate is the point.**
2. **Granularity mismatch.** ce-compound produces a six-section doc (Problem / What Didn't Work /
   Solution / Why / Prevention). `add_insight` and the graph's dedup/conflict/embedding all operate
   per *atomic* fact ("one self-contained sentence or two"). The doc must be **distilled into
   atomic insights**, not stored whole — which is exactly what `CommitIngestor.synthesis` already does
   for PRs.
3. **Provenance.** `add_insight` carries only a `source` string. The ingestion path stamps `source`
   onto every written fact and preserves the audit trail. The rich markdown doc becomes optional
   human-readable provenance, not the source of truth.

## The bridge sketch: a `SessionIngestor`

The bridge is a fourth `Ingestor` variant that mirrors `CommitIngestor` field-for-field — same typed
single-call shape, same precision-first drop-malformed parsing, same closed category set — differing
only in (a) the input it distills and (b) the distillation prompt's framing.

**Input.** ce-compound's Phase 1 already extracts the solved-problem narrative (the Solution
Extractor's sections). Render that into one document string — the analogue of `CommitIngestor`'s
rendered `PRDocument`. No new extraction; reuse what ce-compound already collects.

**Output.** `Insight[]` written `state="proposed"`, `source="session/<id>"`. The section→category
mapping is natural and lets the prompt target the high-signal parts directly:

| ce-compound section | `Insight.category` | `scope` it tends to land in |
|---|---|---|
| What Didn't Work | `rejected` | `file:` or `module:` |
| Prevention | `gotcha` | `file:` (the footgun's site) |
| Why This Works / decisions | `decision` | `module:` or `repo` |
| Conventions established | `convention` | `repo` |

```python
# knowledge/injestion/injestor_variants/session_injestor.py
"""Distill one solved-problem session into Insight[] with a single structured call.

The session analogue of CommitIngestor: same typed {text, scope, category} contract,
same precision-first parsing. Differs only in the distillation prompt's framing —
a debugging/solve narrative rather than a merged PR. Writes state="proposed" by
default (inherited from Ingestor.ingest), so session knowledge enters the candidate
lifecycle and the human gate, NOT the active store directly.
"""
from __future__ import annotations

import json

from knowledge.injestion.injestion_def import Insight
from knowledge.injestion.parent_injestor import Ingestor
from knowledge.knowledge_graph.parent_knowledge_graph import KnowledgeGraph
from knowledge.llm.llm_def import ChatMessage
from knowledge.llm.parent_llm import Llm

_DISTILL_PROMPT = (
    "You are distilling durable engineering knowledge from one solved-problem "
    "coding session for an agent that will work in this repository later.\n"
    "The session narrative names a problem, what was tried and failed, the fix, "
    "why it works, and how to prevent recurrence. Extract ONLY knowledge that stays "
    "true after the fix ships: the root-cause lesson, the gotcha that caused it, the "
    "decision and its rationale, the convention it established, and approaches that "
    "were tried and explicitly rejected.\n"
    "IGNORE the play-by-play: which file was opened first, transient error text "
    "already resolved, and anything restating WHAT was done without WHY it matters "
    "going forward.\n"
    "For each insight return:\n"
    "- text: one self-contained sentence or two, naming its own subject (no pronouns, "
    "no \"this session\"), stating the durable fact and — for a decision or gotcha — "
    "why it holds.\n"
    "- scope: where the fact applies, as `file:<path>`, `module:<name>`, or `repo`.\n"
    "- category: one of decision | gotcha | convention | rejected.\n"
    "Prefer precision over recall: emit nothing rather than a vague or speculative "
    "fact. Return an empty list when the session carries no durable knowledge."
)

_CATEGORIES = ("decision", "gotcha", "convention", "rejected")

# Identical schema to CommitIngestor._SCHEMA — extract to a shared module so the
# two variants cannot drift. (insights[].{text, scope, category}, strict json_schema.)
_SCHEMA = {...}  # see commit_injestor._SCHEMA


class SessionIngestor(Ingestor):
    """Distill a solved-problem session into typed insights with one structured call."""

    def __init__(self, graph: KnowledgeGraph, llm: Llm) -> None:
        super().__init__(graph)
        self.llm = llm

    def synthesis(self, raw_input: str, *, source: str | None = None) -> list[Insight]:
        content = f"{_DISTILL_PROMPT}\n\nSESSION NARRATIVE:\n{raw_input}"
        raw = self.llm.complete(
            [ChatMessage(role="user", content=content)], response_format=_SCHEMA
        )
        try:
            data = json.loads(raw)
        except (TypeError, ValueError):
            return []  # precision-first: non-JSON reply -> nothing distilled
        insights: list[Insight] = []
        for item in data.get("insights", []) if isinstance(data, dict) else []:
            text = str(item.get("text", "")).strip()
            if not text:
                continue  # drop malformed, keep well-formed siblings
            scope = str(item.get("scope", "")).strip() or None
            category = str(item.get("category", "")).strip() or None
            insights.append(
                Insight(raw_text=text, source=source, scope=scope, category=category)
            )
        return insights
```

The diff against `CommitIngestor` is the prompt and the class name. That is the whole point: the two
variants should be **near-identical**, with the `_SCHEMA` (and ideally the shared scaffolding of
`synthesis`) factored into one module so a future schema change touches both at once.

**Where the LLM call is made matters.** `synthesis` calls `Llm.complete`. To keep ce-compound's
in-session experience (the agent already has the narrative in context), the distillation can run
in-session and POST the resulting `Insight[]` to the candidate API as `proposed` candidates — rather
than re-feeding the whole transcript to a backend ingestor. Either way the *destination* is the
candidate lifecycle, and the markdown doc (if kept) is provenance, not the record.

## How ce-compound changes

Minimal, and opt-in per repo (a Praxis-configured project):

- After ce-compound's Phase 1 extraction, run the session narrative through the `SessionIngestor`
  distillation (in-session call) and write the resulting `Insight[]` as `proposed` candidates.
- Keep writing the markdown doc **only** as human-readable provenance, or drop it — the graph fact is
  the record. (In this repo, dropping it changes nothing, since `docs/solutions/` is empty.)
- The Discoverability Check that ce-compound runs against `CLAUDE.md` becomes "agents can reach Praxis
  via `praxis_get_context`," not "agents can grep `docs/solutions/`."

## Key decisions

- **Candidate lifecycle, not `add_insight`.** ce-compound writes `proposed` candidates through the
  `Ingestor` path so the human gate, dedup, and conflict reconciliation all apply. The MCP
  `add_insight` shortcut is reserved for deliberate, single-fact, in-chat approvals — not for
  bulk session distillation.
- **One extractor, one schema, two prompts.** `SessionIngestor` and `CommitIngestor` share the typed
  contract and `_SCHEMA`; they differ only in distillation framing. Factor the schema out so they
  cannot drift.
- **Distill to atomic insights.** The doc's sections map to categories; each becomes one
  `Insight`. Do not store the six-section doc as a single fact.
- **Sequence: write side first, read side gated.** Writing candidates is cheap, reversible, and
  *generates the data the dogfood gate needs*. Cutting recall over to `praxis_get_context` should
  follow the dogfood suite's retrieval gate going clean-green — today it is a strict NO-GO with the
  gap attributed to semantic-only retrieval (see the
  [auto-distill slice](2026-06-24-pr-knowledge-auto-distill-slice.md)). Until then, ce-compound writes
  to Praxis but agents should not yet *rely* on Praxis as their only recall path.

## Requirements

- **R1.** `SessionIngestor` variant alongside `PromptIngestor` / `CommitIngestor`, reusing the
  `Ingestor` contract. Input = rendered session narrative; output = `Insight[]` via one structured
  `Llm.complete` call. `source = "session/<id>"`.
- **R2.** Shared `_SCHEMA` (and `synthesis` scaffolding) extracted from `CommitIngestor` so the two
  variants share one definition.
- **R3.** ce-compound (in a Praxis-configured repo) distills its Phase 1 narrative through R1 and
  writes the insights as `proposed` candidates — landing in the human gate, not `active`.
- **R4.** The markdown doc is optional provenance, not the record. No second flat-file store of truth.
- **R5.** Diagnostic capture mirroring the auto-distill slice's R7: extraction quality (signal-to-noise
  of distilled session insights) and, once read-side lands, retrieval hit rate.

## Success criteria

- Session-distilled insights reach the candidate dashboard as reviewable `proposed` facts with correct
  `scope`/`category` and session provenance, dedup'd against existing facts.
- The `SessionIngestor` / `CommitIngestor` diff is essentially just the prompt — confirming the
  "one extractor, two triggers" framing rather than two divergent pipelines.
- Once the retrieval gate is green, a fresh session retrieves a previously-distilled session fact via
  `praxis_get_context` at the right moment.

## Scope boundaries (deferred)

- **Read-side cutover** — gated on the dogfood retrieval gate (semantic-only retrieval is the known
  weak link; two-lane scope-aware retrieval is the sibling proposal's concern).
- **Auto-supersede vs. human gate for self-captured facts** — same open question the
  [commits-and-PRs proposal](2026-06-24-ingest-commits-and-prs.md) raises; this slice keeps the human
  gate.
- **Headless / automated ce-compound runs writing without review** — out of scope; manual,
  human-confirmed runs first.

## Open questions

1. **Distill in-session or backend?** In-session keeps the narrative warm and avoids re-feeding the
   transcript, but puts the `Llm.complete` call in the agent loop rather than the backend ingestor.
   Decide before planning.
2. **Does the markdown doc survive at all?** Keep as provenance (links from facts back to a readable
   write-up) or drop entirely once the graph is the record?
3. **Scope inference for session facts.** A debugging session names files in its narrative —
   provenance — but where the lesson *applies* is a separate judgment (per the sibling proposal's
   "provenance is not scope"). Does the session prompt need extra guidance to set `scope` well?
4. **Overlap with `CommitIngestor` coverage** — *provisionally resolved: default to dedup, do not
   couple the sources.* A session that ends in a merged PR will be distilled twice (session-end and
   post-merge). The instinct to suppress one trigger (e.g. a `Praxis-Ingested: session/<id>` commit
   trailer the PR ingestor parses and skips) is rejected:
   - **The sources aren't redundant.** The session sees the *journey* (dead ends, the `rejected`-category
     knowledge that never reaches the final diff); the merged PR sees the *reviewed result* — notably
     the review threads, which the [sibling proposal](2026-06-24-ingest-commits-and-prs.md) flags as the
     highest-signal source and which the session never saw. Skipping the PR loses the review-thread
     knowledge.
   - **Double-distillation is a confidence signal, not waste.** Near-duplicate insights merge and bump
     `observation_count` (which exists to raise confidence on repeated independent observation). A
     fact surfaced by both a session and a PR review is *more* trustworthy; a skip mechanism suppresses
     that.
   - **The units don't align.** Session ≠ commit ≠ PR (a session spans commits; a PR bundles commits
     from several sessions; session knowledge can land across PRs), so a commit-level marker can't
     cleanly gate PR-level distillation — and editing the trailer post-hoc fights git timing
     (ce-compound runs after the commit; the PR isn't known until later).

   The cost of the extra LLM call is the only legitimate concern. If measured cost justifies it, the
   right lever is **source-keyed idempotency in the ingestor** (skip a unit whose `source` was already
   ingested) — but note `session/<id>` ≠ `git/pr:<n>`, so that only dedups re-runs of the *same* unit,
   not across session↔PR. Cross-source, dedup the *outputs* (the graph already does), don't couple the
   triggers.
