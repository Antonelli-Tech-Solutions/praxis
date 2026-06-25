# Proposal: Converge `ingest_dump` and the write-policy path where they overlap — keep them distinct where they shouldn't

**Status**: Open / exploratory · **Raised**: 2026-06-24 · **Source**: review of branch `ui/header-tabs-layout`

> The branch `ui/header-tabs-layout` (misnamed — its two commits are pure ingestion work) introduces
> `knowledge/injestion/dump_ingest.py`: a document-scoped "dump" ingestor with slot-granular dedup +
> conflict resolution, motivated by tabular data (tax brackets, W-2 boxes) false-flagging as mutual
> contradictions. This proposal records what should converge with the existing per-fact write policy
> and what should stay deliberately separate.

## Premise (decided, not open)

`ingest_dump` **stays** as a first-class alternate ingestion path for large, self-contained chunks
(documents, tables, dumps) that arrive whole. It is not a stopgap to be folded away. The question is
only *which pieces* it should share with the streaming write-policy path so we don't maintain two
divergent reconciliation engines by accident.

## The two paths are different by design

They are not two implementations of one thing — they are two reconciliation philosophies, each right
for its ingestion mode.

| Dimension | Streaming write-policy path (`main`) | `ingest_dump` (batch) |
|---|---|---|
| Unit | per-fact `graph.write` as facts trickle in | whole document at once |
| Claim source | separate per-fact LLM call (`ClaimExtractor`) | **folded into the distill call** |
| Within-doc dedup | vector recall + per-pair `MergeJudge` | **structural** slot match, no LLM |
| Conflict outcome | flag + edge, **both persist, human resolves** (FR-005, dashboard) | **auto-reject loser, newest wins** |
| Multi-valued safety | `functional` flag on each claim | none (relies on subject granularity) |
| Opinion conflicts | STANCE controlled-vocab tradeoff axes | none |
| Offline/eval | cassette-replayable, deterministic | needs a live key |
| Claim storage | `claims` table | `fact.meta.claim` |

Three of those rows are **fundamental** and must NOT be forced to converge:

1. **Streaming vs batch.** The streaming path reconciles each fact against the existing graph as
   facts arrive (session capture, incremental skill-learning). `ingest_dump` *requires the whole
   document* — that is exactly what lets it match structurally within the batch with no LLM.
2. **`functional` flag + STANCE axes** are real capabilities the dump path lacks. Tabular data
   doesn't need them (attributes are functional; no opinions), so their absence is fine *there* —
   but converging the general path onto the dump path would regress them.
3. **Conflict-resolution philosophy** (see below) — appropriate to content, not to code style.

## What we DO want to converge

### 1. Lift the folded structured-claim extraction into the shared layer

`ingest_dump._distill` already does what we called the "#2 optimization": one structured
`response_format` call returns each fact as `{text, subject, attribute, value}`, instead of a split
call **plus** a separate per-fact `ClaimExtractor` call. Generalize it:

- Let `Insight` carry an optional pre-extracted claim.
- Have `ClaimExtractor.apply` **skip** when `decision.claims` is already populated
  (`knowledge/knowledge_graph/write_policy/write_step_variants/claim_extractor.py`).

Then any ingestor that distills with a claim-aware schema (the dump path today; a future structured
`PromptIngestor`) supplies claims for free, while per-fact extraction stays the fallback for facts
that genuinely arrive one at a time. This is the portable win — the consolidation without imposing
batch semantics on the streaming path.

### 2. Unify claim storage and edge/flag vocabulary

`ingest_dump` writes its claim to `fact.meta.claim` and rejects losers with its own edge handling;
the streaming path writes the `claims` table and records `contradiction:<id>` flags the store
materializes as `fact_edges`. Today these are **parallel universes** — the standard contradiction
surface (dashboard tab) cannot see a dump-path resolution. Converge on:

- one storage location (the `claims` table), and
- one edge/flag vocabulary,

even though the two paths *resolve* conflicts differently. One detector, one audit surface, two
resolution policies.

### 3. Close the offline/eval gap

The streaming path's LLM seams are `VerdictCassette`-replayable, which is what makes the eval harness
deterministic and cheap. `ingest_dump` calls `llm.complete` directly, so its tax eval skips without
`OPENROUTER_API_KEY`. If the dump path is first-class, its distill / `_same_fact` / `_same_slot`
calls need the same cassette treatment, or the two suites diverge in determinism.

## The thing to decide deliberately: conflict-resolution philosophy

This is the real debt the branch introduces, and it is **not** a code-dup issue. With both paths
live, the *same logical contradiction* is handled two completely different ways depending only on
which ingestor touched the data:

- streaming path → persist both, flag, **human resolves** (the elevation surface);
- dump path → silently **reject the loser, newest wins**.

Both are defensible for their content: objective, authoritative dumps (a tax table, a spec) → recency
auto-supersede is fine and avoids drowning a reviewer; subjective or evolving knowledge → human review
matters. The ask is to make this an explicit, documented policy axis — "auto-resolve for authoritative
dumps, elevate for everything else" — selected per ingestion path, rather than an accident of two
implementations. (Note the open `ingest-commits-and-prs` proposal raises the same auto-supersede-vs-gate
question for code facts; this should be one shared decision.)

## Proposed end state

- `ingest_dump` remains the document/batch specialist (structural within-batch dedup, batched
  cross-doc judgments) — **kept by design**.
- The structured folded-claim extraction is shared, not dump-only.
- One claim table, one edge vocabulary, one contradiction surface.
- Conflict-resolution policy is an explicit per-path choice, documented.
- Both paths are cassette-replayable in the eval harness.

## Open questions

1. **Where does the auto-supersede-vs-human-gate switch live** — on the ingestor, the write policy,
   or the source/category of the fact? (Shared with the commits/PRs proposal.)
2. **Does the streaming `PromptIngestor` adopt the structured claim-aware schema**, or stay a plain
   line-splitter with `ClaimExtractor` as its only claim source? (Independent of keeping `ingest_dump`.)
3. **Graph-method surface.** `ingest_dump` needs `all_facts(state=)`, `update_fact`, `delete_fact`,
   `set_state`, `add_edge`, and `write(..., meta=)`. Which become part of the common graph contract vs.
   stay persistence-only?
4. **Multi-valued safety in the dump path.** Without a `functional` flag, a genuinely multi-valued
   attribute whose subjects coincide could false-conflict. Acceptable for tabular data, but does the
   dump path need a `functional` notion before it ingests non-tabular dumps?
5. **Routing.** How does a caller choose dump vs. streaming — explicit API, or a heuristic on input
   size/structure?
