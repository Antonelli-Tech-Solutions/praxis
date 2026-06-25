# Tabular ingestion integrity — eval suite

Encodes the acceptance criteria for the tabular-ingestion-integrity feature
(design: `docs/proposals/2026-06-24-tabular-ingestion-integrity.md`). The feature
closes two independent loss points when ingesting tabular/templated input:

- **A — distillation under-emits / mangles tables** (the `TableLinearizer`).
- **B — the deduper over-merges sibling rows** (the slot-guard in `Deduper`).

## Cases committed here (offline, no models, no embedder)

These run fully offline and deterministically — they exercise **loss point A** via
the no-LLM `segment_passthrough` path. RED on pre-feature code (raw table syntax
survives), GREEN once the linearizer lands.

| Case | Table shape | Proves |
|---|---|---|
| `linearize_field_table_offline` | field → required (subject varies per row) | every row → one clean fact, no pipe/separator artifacts |
| `linearize_role_permission_table_offline` | role × permission (same subject, attribute varies) | same-subject rows each survive distinctly |

Run them:

```
uv run pytest knowledge/evals/tests/test_cases.py -k tabular
```

## Cases to add AFTER loss point B lands (model-dependent — record cassettes first)

The slot-guard (B) only manifests when the **MergeJudge / conflict path** is live,
which needs a real embedder + committed verdict cassettes. These cannot be committed
yet because a cassette/embedding miss is a deliberate **loud error** offline. Add
them once B is merged and a key is available to record.

Critical wiring precondition: the guard engages only when the write carries
`TABULAR_FLAG` (exported from
`knowledge/knowledge_graph/write_policy/write_step_variants/deduper.py`). The
linearizer (A) must stamp that flag on facts distilled from detected tables, or the
guard stays dormant. Verify that wiring before recording these.

Planned cases (mirror `dom/semantic_dedup/ingestion_merge_near_dupes` and
`matt/claim_no_conflict_distinct_subjects` for structure):

1. **`sibling_rows_no_overmerge`** — `component: knowledge_graph`, `substrate: vector`,
   `embedder: cached`, `merge_model: openai/gpt-4o-mini`. Seed two same-template rows
   that differ only by key (e.g. role×permission). Assert BOTH survive as distinct
   facts (not merged into one) — the guard overriding a "same lesson" judge verdict.
2. **`same_slot_value_conflict`** — `embedder: cached`, `conflict_model: openai/gpt-4o-mini`.
   Seed two rows with the **same `(subject, attribute)` slot but conflicting values**.
   Assert exactly one contradiction is flagged
   (`text:occurs_exactly`, `text: "CONTRADICTION"`, `n: 1`) — proving the guard routes
   case 2 to the conflict engine rather than silently suppressing the merge.
3. **`tabular_idempotent_reingest`** — re-ingest the same table twice; assert N facts,
   not 2N (same-slot/same-value → legitimate merge preserved).

Recording (once B is merged and `OPENROUTER_API_KEY` is set):

```
# records embedding vectors + verdict cassettes for the new embedder:cached cases
OPENROUTER_API_KEY=... uv run python -m knowledge.evals.embed_cache   # refresh vectors
OPENROUTER_API_KEY=... uv run pytest knowledge/evals/tests/test_cases.py -k tabular  # records verdict cassettes
```

Commit the recorded `*.json` cassettes/vectors so the cases replay offline in CI.
