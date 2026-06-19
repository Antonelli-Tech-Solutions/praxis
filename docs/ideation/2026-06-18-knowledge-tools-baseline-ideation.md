---
date: 2026-06-18
topic: knowledge-tools-baseline
focus: upgrade ingestion / knowledge_graph / graph_reader from MVP stubs to a credible best-practices baseline
mode: repo-grounded
---

# Ideation: A credible baseline for the Praxis knowledge tools

## Grounding Context

**Codebase context.** Today the three knowledge tools are deliberate stubs: `Ingestor.synthesis` (no-LLM passthrough that splits text into lines), `KnowledgeGraph` = an in-memory string (`InMemoryGraph`, append-on-write), `GraphReader` = whole-file return (ignores context). The architecture is **frozen contracts + swappable variants**: each stage is a `parent_*` ABC with a concrete orchestration method (`ingest`, `read`) and one abstract `synthesis` step; variants live under `*_variants/` and are wired in `wiring.build_trio`. Two semantics are load-bearing: `KnowledgeGraph.write` is **integrate/append, not replace** (ingestion calls it once per insight), and `read(context)` *may* ignore context — so a real reader must filter itself via `ReadRequest`. The data models are intentional one-field stubs with named extension points: `Insight{raw_text}` ("→ source, confidence, tags") and `ReadRequest{query}` ("→ filters, top-k, section selectors"). A 50+ case eval corpus already encodes the target capabilities, many as **expected-FAIL baselines that flip to PASS when the capability lands** (e.g. `ingestion_dedup`, `ingestion_drop_secret`, `lost_in_middle`, `context_budget_overload`, `scoped_conflict`, `recency_tiebreak_newer_wins`).

**External context (SOTA, 2024–2026).** Agent-memory landscape: **Mem0** (extraction → embed → ADD/UPDATE/DELETE/NOOP classify; self-hostable, sqlite/Chroma/LanceDB backends), **Zep/Graphiti** (bi-temporal knowledge graph on Kùzu, top LongMemEval scores), Letta/MemGPT (heavy runtime), Cognee, A-MEM. Retrieval consensus stack: **BM25 + dense + Reciprocal Rank Fusion (k=60) + cross-encoder rerank** (`rank_bm25`, `sentence-transformers`, `bge-reranker-v2-m3`); query rewriting via **HyDE** / multi-query; **lost-in-the-middle** (Liu 2023) mitigated by score-ordered edge placement + token budget. Stores: **sqlite-vec** / **LanceDB** (embeddable vectors), **Kùzu** (embeddable graph). Extraction: Pydantic + function-calling schemas (PARSE), triple extraction (KGGen, OneKE), **Presidio** for PII redaction. GraphRAG (community summaries) is powerful but 3–5× indexing cost — beyond baseline.

**Past learnings.** No `docs/solutions/` exists yet — the only prior decisions are the frozen contracts, the data-model docstrings, and the eval corpus. Recommendation echoed by the learnings pass: build new `*_variants` against the existing interfaces, preserve append/`write` + self-filtering-`read` semantics, and make the eval corpus the definition of done.

## Topic Axes

- Ingestion / distillation (raw turns → structured, deduped, safe insights)
- Knowledge store / representation (the substrate behind `KnowledgeGraph`)
- Retrieval / reader (turning context into the right slice of knowledge)
- Schema & measurement (typed contracts + proving the baseline actually helps)

## Ranked Ideas

### 1. Extend the typed contracts: `Insight` and `ReadRequest`
**Description:** Grow `Insight{raw_text}` → `{claim, category(Literal[error_fix|constraint|pattern|api_behavior]), entities, source_session/turn, confidence, scope, observation_count, last_seen}` and `ReadRequest{query}` → `{query, top_k, filters, scope}`. Everything else depends on these fields existing.
**Axis:** Schema & measurement
**Basis:** `direct:` the docstrings literally name the Phase-2 fields ("Insight → source, confidence, tags"; "ReadRequest → filters, top-k, section selectors"), and the eval harness already mirrors these models.
**Rationale:** Schema discipline is the cheapest move with the most compounding downstream value — dedup keys, confidence thresholds, scope filtering, provenance, and top-k retrieval all become trivial once the fields exist; bolting them on later means reworking every variant.
**Downsides:** Touches shared models; must keep them backward-compatible with the 50+ existing cases (additive, defaulted fields).
**Confidence:** 95% · **Complexity:** Low · **Status:** Unexplored

### 2. Structured extraction distiller (replace the passthrough `synthesis`)
**Description:** A `StructuredIngestor` variant whose `synthesis` calls an LLM (function-calling + Pydantic) to score each turn for reuse value, then emit atomic `Insight`s with category/entities/provenance/confidence — extractive, not abstractive.
**Axis:** Ingestion / distillation
**Basis:** `external:` Mem0 extraction pipeline (arxiv 2504.19413) + PARSE schema-guided extraction (2510.08623); `direct:` flips `ingestion_strip_noise_keep_signal` and `ingestion_retain_provenance`, and the proposal favors extractive distillation.
**Rationale:** This is the step that turns a transcript into reusable knowledge; without it everything downstream operates on noise. Provenance + confidence captured here are what later enable poison-resistance and decay.
**Downsides:** Adds an LLM call per ingest (cost/latency); extraction quality is prompt-sensitive — needs the eval corpus to keep it honest.
**Confidence:** 85% · **Complexity:** Medium · **Status:** Unexplored

### 3. Write-time integration policy: dedup + conflict + redaction
**Description:** On `write`, run the Mem0-style decision — embed the candidate, nearest-neighbor lookup, LLM classify ADD/UPDATE/DELETE/NOOP — plus a contradiction check against top-k similar facts and a redaction gate (Presidio for PII + entropy/regex for secrets) that blocks before storage.
**Axis:** Ingestion / distillation
**Basis:** `external:` Mem0 ADD/UPDATE/DELETE/NOOP, `datasketch` MinHash, Microsoft Presidio; `direct:` flips the expected-FAIL cases `ingestion_dedup`, `ingestion_merge_near_dupes`, `ingestion_drop_secret`, `ingestion_redact_pii`, and feeds `contradiction_should_flag` / `overturn_explicit`.
**Rationale:** This is the primary defense against the central risk (negative compounding) — a store that appends blindly poisons itself. Redaction is a hard requirement, not a stretch goal.
**Downsides:** Requires the store to support lookup/update (couples to idea 5); contradiction detection adds LLM calls; over-aggressive merge can drop nuance.
**Confidence:** 85% · **Complexity:** Medium · **Status:** Unexplored

### 4. Embedded vector+metadata store as a `KnowledgeGraph` variant
**Description:** A `VectorGraph` variant backed by **sqlite-vec** (single-file, zero-infra): a `facts` table with `claim, embedding, category, scope, source, confidence, observation_count, last_seen`. Preserves append/integrate `write` semantics; adds the similarity lookup ideas 3 and 6 need.
**Axis:** Knowledge store / representation
**Basis:** `external:` sqlite-vec / LanceDB as the lightweight embeddable baseline; `direct:` the contract explicitly invites store variants, and cases `kg_capacity` / `scoped_conflict` need real fields + scope.
**Rationale:** The in-memory string is the bottleneck — no similarity, no metadata, no durability. sqlite-vec gets a structured, queryable, persistent substrate with essentially no operational cost.
**Downsides:** Embedding model dependency; sqlite-vec is single-process (fine for now); a migration story for the in-memory variant in tests.
**Confidence:** 88% · **Complexity:** Medium · **Status:** Unexplored

### 5. Hybrid retrieving reader: BM25 + dense + RRF + rerank + budget
**Description:** A `RetrievingReader` variant whose `synthesis` turns agent context into `ReadRequest`s (optionally HyDE/multi-query rewriting), then `read` runs BM25 + dense retrieval, fuses with RRF (k=60), reranks the top-N with a cross-encoder, and assembles results under a token budget with score-ordered edge placement (lost-in-the-middle mitigation).
**Axis:** Retrieval / reader
**Basis:** `external:` the production consensus stack (RRF, `bge-reranker-v2-m3`, Liu 2023 lost-in-the-middle); `direct:` `WholeFileReader` returns the entire graph today, and cases `lost_in_middle`, `context_budget_overload`, `near_miss_distractor` are expected-FAILs aimed exactly here.
**Rationale:** Retrieval is where "the knowledge graph helps" is won or lost — whole-file injection guarantees context rot as the store grows. This is the single highest-leverage reader move and most of it is ~tens of lines + off-the-shelf models.
**Downsides:** Reranker adds latency; needs the vector store (idea 4) for the dense arm; query-rewriting can hallucinate — gate it behind the eval cases.
**Confidence:** 90% · **Complexity:** Medium · **Status:** Unexplored

### 6. Make the baseline measurable: cold arm + eval-driven build
**Description:** Add a **cold arm** to `run_case` (`behavior(injected) − behavior(cold)`) so lift is measurable, and drive the whole upgrade by flipping the corpus's expected-FAIL cases green one capability at a time (component evals first — deterministic/fast — then full-pipeline).
**Axis:** Schema & measurement
**Basis:** `direct:` the 50+ case corpus is pre-written acceptance criteria with documented expected-FAILs; the cold arm was already flagged as the missing enabler for lift/no-harm cases.
**Rationale:** Without lift measurement you can't tell whether a richer store/reader actually helps or just adds cost — and negative compounding is invisible. This turns the upgrade from "felt better" into a gated number, which is the project's whole thesis.
**Downsides:** Cold arm doubles agent runs for full-pipeline cases (bounded by running it only where it matters); some cases stay rubric-graded.
**Confidence:** 88% · **Complexity:** Low–Medium · **Status:** Unexplored

### 7. Scope & confidence as first-class retrieval filters
**Description:** Carry `scope` (service / directory / global) and `confidence` on facts and honor them in retrieval: filter by active scope, drop facts below a confidence threshold, and break ties by recency. Apply decay (`effective_weight = confidence · recency_half_life`).
**Axis:** Knowledge store / representation
**Basis:** `external:` provenance-aware tiered memory (2602.17913), recency-decay patterns; `direct:` cases `scoped_conflict`, `over_generalization`, `confidence_below_threshold_ignored`, `recency_tiebreak_newer_wins` target exactly this.
**Rationale:** The non-obvious failures (a `legacy/`-only rule bleeding into new code; a stale low-confidence rumor overriding an enforced rule) are conflict/scope problems, not retrieval-quality problems — and they're the ones most likely to degrade real sessions.
**Downsides:** Requires scope to be inferred at ingest or supplied by the runner; thresholds/half-life need tuning against the corpus.
**Confidence:** 80% · **Complexity:** Medium · **Status:** Unexplored

## Recommended sequencing

1 (contracts) → 4 (vector store) → 6 (cold arm + eval-driven) in parallel with → 2 (extraction) → 3 (write-time policy) → 5 (retrieving reader) → 7 (scope/confidence filters). Schema and measurement first so every later move is gradable; store before the ingestion/reader moves that depend on similarity lookup.

## Rejection Summary

| # | Idea | Reason Rejected |
|---|------|-----------------|
| 1 | Adopt Mem0 wholesale as the engine | Heavy dependency + opinionated lock-in; its techniques (extract, ADD/UPDATE/DELETE/NOOP) are already captured by ideas 2–4 as in-house variants behind the frozen contracts |
| 2 | GraphRAG community summaries / global search | Too expensive (3–5× indexing cost) relative to value at current corpus size; revisit for cross-session "what recurs" queries later |
| 3 | Bi-temporal KG (Graphiti + Kùzu) | Beyond a *baseline* — valuable once recurring entities + "what did the agent know at session N" matter; sequencing, not merit (keep on the roadmap) |
| 4 | Full entity/relation triple KG (KGGen / OneKE) | Heavier; premature before the vector baseline (idea 4) proves out the simpler representation |
| 5 | HyPE (index-time hypothetical queries) | Moderate index overhead; folded into idea 5 as optional HyDE/multi-query rewriting instead of a standalone move |
| 6 | Letta / MemGPT runtime | Wrong shape (autonomous-agent OS runtime), heavy; not a store/reader baseline |
| 7 | Learning-moment signal detection (standalone) | Duplicate — folded into idea 2's extraction prompt (per-turn reuse scoring) |
| 8 | Scope/namespace as a standalone store feature | Duplicate — folded into ideas 4 (scope field) and 7 (scope-aware retrieval) |
| 9 | "Wrap as variants preserving contracts" | Not an idea — it's the implementation constraint governing all of the above (build new `*_variants`, register in `build_trio`, keep append/self-filter semantics) |
