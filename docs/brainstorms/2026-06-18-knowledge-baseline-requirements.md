---
date: 2026-06-18
topic: knowledge-baseline
status: requirements
origin: docs/ideation/2026-06-18-knowledge-tools-baseline-ideation.md
---

# Requirements: Knowledge-tools baseline (Minimal + safety)

## Outcome

Replace the MVP stubs for the three knowledge tools with a credible baseline — a real vector-backed store, a write-time safety pipeline, and a retrieving reader — built to the project's architectural bar: **strict OOP, code in the right folders, highly readable and decomposable, and faithful to the established `parent_* / *_variants / *_def` pattern and the frozen contracts.** The eval corpus is the acceptance test.

This is the "Minimal + safety" cut from the ideation doc: ideas **1 (contracts), 3 (write-time policy), 4 (vector store), 5 (retrieving reader)**, plus the shared LLM/embedding seam and a per-case substrate selector.

## Validated architectural decisions

1. **Search is a capability interface, not a base-contract change.** A new `SearchableGraph(KnowledgeGraph)` ABC adds `search`. `VectorGraph` implements it; `RetrievingReader` depends on `SearchableGraph`. The frozen `KnowledgeGraph` (read/write) and the `GraphReader`/`Ingestor` contracts are untouched — capability is added by interface segregation, not by widening the base.
2. **The write-time policy is a composable pipeline owned by the store.** `VectorGraph` composes an ordered list of small single-responsibility steps — Redact → Dedup/merge → Conflict-flag — each its own class/file. `write()` runs the pipeline, then persists. The store owns it because dedup/conflict need the store's own similarity search.
3. **The embedding/LLM seam is a shared package mirroring the established pattern.** New `knowledge/llm/` with `parent_embedder` + `embedder_variants/{openrouter,fake}`, `parent_llm` + `llm_variants/{openrouter,fake}`, and `llm_def`. The OpenRouter HTTP client moves out of `knowledge/evals/` into this shared home; `knowledge/evals/openrouter.py` re-imports it. Core knowledge code never imports up from `evals/`.
4. **Substrate is selected per eval case.** `EvalCase` gains `substrate: in_memory | vector` (default `in_memory`); `build_trio(substrate)` picks the wiring. The existing 53 cases stay on `in_memory` and deterministic; capability cases opt into `vector` and stay deterministic in CI via the seam's Fake embedder/LLM variants. (Matches the documented future-work `substrate` field.)

## Component responsibilities (the WHAT, not signatures)

- **Contracts (`*_def`)** — `Insight` gains `source`, `confidence`, `scope`, `category`, `observation_count` (additive, defaulted). `ReadRequest` gains `top_k`, `filters`, `scope`. A store-facing `Fact`/search-result shape is defined alongside the graph contract.
- **Store** — `VectorGraph(SearchableGraph)` on `sqlite-vec`: append-integrate `write` runs the policy pipeline then persists; `search` does similarity lookup. Preserves the frozen append (not replace) semantics.
- **Write-policy steps** — `Redactor` (PII via Presidio + secret regex/entropy), `Deduper` (embed → nearest-neighbor → ADD/UPDATE/DELETE/NOOP), `ConflictFlagger` (retrieve similar → flag contradictions). Each independently testable and swappable.
- **Reader** — `RetrievingReader(GraphReader)` depends on `SearchableGraph`: `synthesis` turns context into `ReadRequest`(s); `read` runs the retrieval pipeline — sparse (BM25) + dense + RRF fusion + cross-encoder rerank + token-budget/edge-ordered assembly — as small composable retriever objects.
- **Ingestion** — unchanged for this cut (passthrough distiller still feeds `write`); the policy pipeline at the store provides the safety. Structured LLM extraction is deferred.
- **Wiring** — `build_trio(substrate)` returns the in-memory trio or the vector trio (`VectorGraph` + ingestor + `RetrievingReader`).

## Folder placement (repo-relative)

- `knowledge/llm/` — new shared seam (parent + variants + `_def`); OpenRouter client relocates here.
- `knowledge/knowledge_graph/parent_searchable_graph.py` — the capability interface; `knowledge_graph_def.py` — `Fact`/result shape.
- `knowledge/knowledge_graph/knowledge_graph_variants/vector_graph.py` — the store; `knowledge/knowledge_graph/write_policy/` — `parent_write_step.py` + `write_step_variants/{redactor,deduper,conflict_flagger}.py`.
- `knowledge/graph_reader/grapher_reader_variants/retrieving_reader.py` + `knowledge/graph_reader/retrieval/` — the small retriever steps.
- `knowledge/injestion/injestion_def.py` — extended `Insight`; `knowledge/graph_reader/graph_reader_def.py` — extended `ReadRequest`.
- `knowledge/wiring.py`, `knowledge/evals/eval_def.py`, `knowledge/evals/run.py` — substrate selection.

## Scope boundaries

**In scope:** the four decisions above and the components they name — contracts, vector store + write-policy pipeline, retrieving reader, shared seam, per-case substrate.

**Deferred (next pass):** structured LLM extraction quality (ideation #2 — the passthrough distiller stays for now), scope-aware retrieval filtering + confidence decay (#7 — `scope`/`confidence` fields are carried now but not yet used to filter/rank), the eval cold arm (#6).

**Outside this baseline:** bi-temporal KG / Graphiti, GraphRAG community summaries, full triple-extraction KGs, Mem0/Letta as wholesale engines. (On the roadmap, not now.)

## Success criteria

- Frozen base contracts unchanged; capability added only via `SearchableGraph`. No `knowledge/` module imports from `knowledge/evals/`.
- Every new responsibility (each policy step, each retriever step, each seam variant) is its own small, independently unit-tested class, in the folder its component owns.
- The existing 53 eval cases stay green on `in_memory` and offline-deterministic.
- On the `vector` substrate (with Fake seam in CI), these expected-FAIL cases flip green: `ingestion_dedup`, `ingestion_merge_near_dupes`, `ingestion_drop_secret`, `ingestion_redact_pii`, `near_miss_distractor`, `lost_in_middle`, `context_budget_overload`; `kg_*` stay green.

## Outstanding questions (for planning)

- Conflict-flag mechanism: embedding-similarity + heuristic vs. an LLM call (Fake-backed for deterministic tests).
- Concrete choices: embedding model via OpenRouter, dedup cosine threshold, RRF `k` (default 60), reranker (local `bge-reranker` vs API).
- `sqlite-vec` schema specifics and whether `InMemoryGraph` stays search-less (only `VectorGraph` implements `SearchableGraph`).
- Whether redaction should *also* run defense-in-depth at ingestion, or stay store-only (currently store-only).
