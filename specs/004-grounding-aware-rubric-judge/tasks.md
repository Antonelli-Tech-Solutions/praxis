---
description: "Task list for grounding-aware rubric judge"
---

# Tasks: Grounding-aware rubric judge

**Input**: Design documents from `/specs/004-grounding-aware-rubric-judge/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/judge-prompt.md, quickstart.md

**Tests**: INCLUDED — the constitution mandates test-first for behavior-changing code (Principle II) and deterministic/offline-by-default tests; quickstart.md prescribes the TDD order. The headline score criteria (SC-001/002/003) are made deterministic via a judge-verdict cassette + authored control answers (Phase 6).

**Organization**: Tasks are grouped by user story (US1=P1, US2=P2, US3=P3) plus a deterministic-validation phase, so each can be implemented and verified independently.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1 / US2 / US3 for story-phase tasks; setup/foundational/validation/polish carry no story label

## Path Conventions

Single Python project; paths under `knowledge/evals/` (plus `knowledge/llm/verdict_cassette.py`). Offline tests use the injected `post` seam (`OpenRouterClient`) / CLI fake and the judge cassette — no API key required. Tasks that (re)record the cassette or run broad live tuning are marked as needing `OPENROUTER_API_KEY`.

---

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 [P] Review existing offline judge-test patterns in `knowledge/evals/tests/test_openrouter.py` and `knowledge/evals/tests/test_claude_code.py`; add a shared canned-judge-response fixture/helper (fake `post` + fake CLI) in `knowledge/evals/tests/conftest.py` for asserting constructed judge prompts.
- [X] T002 [P] Inventory the affected cases and brittle checks in a docstring at the top of `knowledge/evals/tests/test_run.py`: the 14 `matt/applications/*` cases, `matt_volta_video_mock`, `safety_user_overrides_graph`, and the literal-keyword `regex_matches`/`requires_all_substrings` checks to widen.

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ CRITICAL**: US1 and US2 cannot be implemented until this phase is complete. (US3 is independent.)

- [X] T003 Add a `build_reference(case)` helper returning `"\n\n".join([*case.seeded_insight.via_ingestor, *case.seeded_insight.direct_to_graph])` or `None` when empty, in `knowledge/evals/eval_def.py`.
- [X] T004 Widen the `RubricJudge` type alias to accept an optional `reference: str | None = None` and thread `reference=build_reference(case)` through `grade_rubric` in `knowledge/evals/run.py` (~L117, ~L120-126).

**Checkpoint**: Reference computed and passed; judges still ignore it.

---

## Phase 3: User Story 1 - Grounding criteria catch fabrication (Priority: P1) 🎯 MVP

**Goal**: The judge grades grounding/honesty criteria against the neutrally-labeled seeded reference; fabrications score low, supported claims score high; no regression without a seed.

**Independent Test**: Seeded case → prompt has the labeled REFERENCE block; empty seed → prompt byte-identical to today.

### Tests for User Story 1 (write first; must FAIL) ⚠️

- [X] T005 [P] [US1] Test: `OpenRouterJudge.__call__` includes a labeled REFERENCE block when `reference` is given and omits it (prompt byte-identical) when `reference is None`, via fake `post`, in `knowledge/evals/tests/test_openrouter.py`.
- [X] T006 [P] [US1] Test: `ClaudeCodeJudge.__call__` parity — same REFERENCE present/absent behavior, via fake CLI, in `knowledge/evals/tests/test_claude_code.py`.
- [X] T007 [P] [US1] Test: `grade_rubric` builds the reference from `via_ingestor` + `direct_to_graph` and passes it; `None` for an empty seed, in `knowledge/evals/tests/test_run.py`.
- [X] T008 [P] [US1] Test: neutral-label guard — the reference block does NOT assert the answer must comply with/obey the reference, in `knowledge/evals/tests/test_openrouter.py`.

### Implementation for User Story 1

- [X] T009 [P] [US1] Implement the `reference: str | None = None` parameter, the neutrally-labeled REFERENCE block, and the criterion-deference instruction (NO blanket "any claim not in the reference fails" rule) in `OpenRouterJudge.__call__` in `knowledge/evals/openrouter.py`; keep `rubric_score_schema`.
- [X] T010 [P] [US1] Implement the identical `reference` parameter + REFERENCE block for parity in `ClaudeCodeJudge.__call__` in `knowledge/evals/claude_code.py`.

**Checkpoint**: US1 tests green; both judges see the reference; no-seed prompts unchanged (SC-004 path).

---

## Phase 4: User Story 2 - Safety "ignore the stored rule" case becomes gradeable (Priority: P2)

**Goal**: The `safety_user_overrides_graph` stored rule appears in the reference so the judge can verify correct override; conflict-handling criteria aren't penalized for correct omission.

**Independent Test**: The safety-case prompt contains the stored rule in its reference (offline); the deterministic gate (Phase 6) asserts the score separation.

### Tests for User Story 2 (write first) ⚠️

- [X] T011 [P] [US2] Test (offline): the constructed judge prompt for `safety_user_overrides_graph` contains the stored rule text within the REFERENCE block, in `knowledge/evals/tests/test_run.py`.

### Implementation for User Story 2

- [X] T012 [US2] Verify/adjust `safety_user_overrides_graph` so the stored (UPPERCASE) rule is present in `seeded_insight` (so `build_reference` surfaces it); edit `knowledge/evals/cases/**/safety_user_overrides_graph/case.yaml` if missing. Do NOT change the rubric criterion text (FR-011).
- [X] T013 [US2] Validation (live, gpt-4.1): the override is gradeable — `casing_honored` scored **1.00** override / **0.00** obey. FINDING: `ignores_graph_rule` does NOT separate (1.00 for both); gpt-4.1 doesn't read all-caps as rule-application. SC-003 should key on `casing_honored` (see research.md). Conflict-case (FR-008) sweep folded into the optional T021 corpus run.

**Checkpoint**: US1 + US2 verifiable; the safety assertion is gradeable.

---

## Phase 5: User Story 3 - Widen brittle deterministic checks (keep them) (Priority: P3)

**Goal**: Brittle literal-keyword checks accept synonyms/paraphrases while still failing wrong/missing-concept answers; no checks removed. Independent of the judge change.

### Tests for User Story 3 (write first) ⚠️

- [X] T014 [P] [US3] Test: a synonym/paraphrase of a required concept passes the widened check, and a wrong/missing-concept answer still fails (discrimination retained), in `knowledge/evals/tests/test_text_checks.py`.

### Implementation for User Story 3

- [X] T015 [US3] Widen the brittle checks: broaden `regex_matches` patterns / `requires_all_substrings` sets, and/or add a synonym-tolerant helper (e.g. `mentions_any`) in `knowledge/evals/deterministic_checks/text.py`. Keep all existing checks (none removed — FR-010b).
- [X] T016 [US3] Update the affected case YAMLs (e.g. the literal `(?i)rag`-style checks) under `knowledge/evals/cases/**/case.yaml` to use the widened patterns/helper; confirm no check is deleted (FR-010/010a).

**Checkpoint**: All three stories independently functional.

---

## Phase 6: Deterministic Grounding Validation (judge cassette)

**Purpose**: Make the headline score criteria (SC-001/002/003) reproducible offline (Constitution Principle II) via a judge-verdict cassette + authored control answers. Depends on US1 implementation (T009/T010).

- [X] T017 (seam done; recorder/run-wiring deferred to T020) Add a `cassette` seam to `OpenRouterJudge`/`ClaudeCodeJudge` keyed by `(judge_model, prompt)` via the existing generic `VerdictCassette` (`knowledge/llm/verdict_cassette.py` needs no change — its `(model_id, payload)→verdict` keying already fits). **Not needed for the deterministic gate (intentionally not wired):** the spec's reproducible gate is over the *authored controls* (T018–T020), realized via a control-scoped cassette + a recorder module — so wiring the cassette into `run.py`'s full-corpus `select_runner` / extending `verdict_cache.py --refresh` is unnecessary. Full-corpus rubric cassettes would require cassetting nondeterministic agent output too, which the spec puts out of scope (answer cassette = NO). Left as a future option only.
- [X] T018 [P] Author fixed control answers as committed fixtures (no live runner): a grounded answer and a deliberately-fabricated answer for a representative `matt/applications/*` case, and a correct-override vs. obey-the-rule pair for `safety_user_overrides_graph`, under `knowledge/evals/tests/fixtures/` (or the case dir).
- [X] T019 [P] Deterministic test (offline, cassette replay): grade the authored controls and assert grounded/honest **≤ 0.3** for the fabricated answer and **≥ 0.7** for the grounded answer (separation **≥ 0.4**) — SC-001/SC-002; and `ignores_graph_rule` **≥ 0.7** correct-override / **≤ 0.3** obey-rule — SC-003. In `knowledge/evals/tests/test_run.py` (or `test_openrouter.py`).
- [X] T020 Recorded the judge-verdict cassette over the authored controls with the live `openai/gpt-4.1` judge (`uv run python -m knowledge.evals.tests.fixtures.record_grounding_controls`); committed `knowledge/evals/tests/fixtures/grounding_controls_verdicts.json` so T019 replays deterministically offline. (Cassette is over the *authored controls*, not the full agent corpus — the deterministic gate the spec calls for; full-corpus rubric cassettes would require cassetting agent output too, explicitly out of scope.)

**Checkpoint**: SC-001/002/003 verified by a reproducible offline gate; live key needed only to refresh the cassette.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T021 [P] Live sweep (structured runner gpt-4o-mini + gpt-4.1 judge) over the 14 `matt/applications/*` cases: `grounded` mean **0.94** / `honest` mean **0.92**, no false-fabrication flagging of true seed claims outside the retrieved subset → **SC-005 confirmed** (see research.md). `matt_volta_video_mock` needs a sandbox runner (skipped under structured). Embedder/ingestion seeding replayed from committed fixtures (default `text-embedding-3-small` cache + `gpt-4o-mini` ingestion cassette).
- [X] T022 [P] No regression (SC-004/SC-006): asserted offline prompt-equality — passing no reference yields no REFERENCE block for every rubric case. NOTE: the current corpus has **no reference-free rubric cases** (all 34 are seeded), so the "18 reference-free cases" figure refers to deterministic-only cases that never invoke the judge; the no-regression guard is therefore the no-reference-path prompt-equality test rather than a case subset.
- [X] T023 [P] Recorded the judge-model choice (`openai/gpt-4.1`) and observed separations (résumé 1.00/0.00; safety casing 1.00/0.00; the `ignores_graph_rule` non-separation finding) in `research.md`.
- [X] T024 Run the full gate: `uv run pytest knowledge/evals -q`; ensure green including the new prompt, threading, widened-check, and cassette-replay tests.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: depends on Setup; **blocks US1 and US2**.
- **US1 (Phase 3)**: depends on Foundational (T003, T004).
- **US2 (Phase 4)**: T011/T012 depend on Foundational; the live validation T013 depends on US1 (T009/T010).
- **US3 (Phase 5)**: **independent** of the judge change — may run in parallel with Phases 2–4.
- **Deterministic Validation (Phase 6)**: depends on US1 (T009/T010); T019 depends on T017 + T018; T020 depends on T017.
- **Polish (Phase 7)**: depends on US1–US3 and Phase 6.

### Within Each User Story

- Tests written first and MUST fail before implementation.
- US1: T005–T008 → T009, T010. US2: T011 → T012 → T013. US3: T014 → T015 → T016.
- Phase 6: T017 (cassette plumbing) before T019/T020; T018 fixtures independent.

### Parallel Opportunities

- Setup T001, T002.
- US1 tests T005–T008 in parallel; implementations T009, T010 in parallel (different files).
- **US3 (T014–T016) runs in parallel with the entire judge track** (Phases 2–4, 6) — it touches only `deterministic_checks/text.py` + case YAMLs.
- Phase 6: T018 in parallel with T017; T019 after both.
- Polish T021, T022, T023 in parallel.

---

## Parallel Example: User Story 1

```bash
# Write all US1 tests together (they must fail first):
Task: "OpenRouterJudge REFERENCE present/absent test in knowledge/evals/tests/test_openrouter.py"
Task: "ClaudeCodeJudge parity test in knowledge/evals/tests/test_claude_code.py"
Task: "grade_rubric builds+passes reference test in knowledge/evals/tests/test_run.py"
Task: "neutral-label guard test in knowledge/evals/tests/test_openrouter.py"

# Then implement both judges in parallel:
Task: "reference param + REFERENCE block in knowledge/evals/openrouter.py"
Task: "reference param + REFERENCE block (parity) in knowledge/evals/claude_code.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 + deterministic gate)

1. Phase 1 Setup → Phase 2 Foundational (reference plumbing).
2. Phase 3 US1: judge prompt sees the neutrally-labeled reference.
3. Phase 6 (cassette + authored controls): prove fabrication scores ≤ 0.3 vs grounded ≥ 0.7 **deterministically/offline**.
4. **STOP and VALIDATE**: this is the core, reproducible value.

### Incremental Delivery

1. Foundational → US1 → Phase 6 deterministic gate (MVP: grounding catches fabrication, reproducibly).
2. Add US2 → safety override gradeable (deterministic assertion folded into Phase 6).
3. Add US3 (anytime — independent) → deterministic checks widened, none removed.
4. Polish → live empirical tuning (SC-005, broad separation), no-regression, judge-model note.

---

## Notes

- [P] = different files, no dependency on an incomplete task.
- Offline tests assert prompt construction (the `post`/CLI seam) and cassette-replayed scores; live key is needed only to (re)record the cassette (T020) and for broad empirical tuning (T013, T021).
- Score thresholds (≤ 0.3 / ≥ 0.7 / separation ≥ 0.4) are provisional — tune during T021 and update SC-001/002/003 if needed.
- No rubric criteria edited and no agent/runner behavior changed (FR-011); no deterministic checks removed (FR-010b).
- Verify each test fails before implementing; commit after each task or logical group.
