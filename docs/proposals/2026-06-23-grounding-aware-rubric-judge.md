# Proposal: grounding-aware rubric judge

**Owner:** Dominic Antonelli — eval harness
**Status:** Proposed
**Date:** 2026-06-23
**Scope:** the rubric judge (`OpenRouterJudge`, and the Claude judge by parity) — what context it grades against. Eval-infra only.
**Relates to:** [`2026-06-23-active-fact-retrievability.md`](completed/2026-06-23-active-fact-retrievability.md) (grounding prerequisite, now landed) and the `model-robust-recall-policies` FR-030/SC-013 application-suite validation.

> The rubric judge grades each criterion from the **rubric text + the answer only** — it is never handed the source knowledge. So the criteria that need the ground truth (`grounded`, `honest`) can't actually be evaluated: the judge scores *plausibility*, not *support*. Give it the (now-populated) reference and tell it to verify against it.

## 1. Problem

`OpenRouterJudge.__call__` builds its prompt as `RUBRIC + ARTIFACT(ctx.output)` — it never includes `ctx.injected_knowledge`. For the `matt/applications/*` rubric that means **3.5 of 6.0 criterion-weight is unverifiable**:

| Criterion | Weight | Verifiable from output alone? |
|-----------|-------:|-------------------------------|
| `grounded` ("no fabricated employers/projects/metrics") | 2.0 | ❌ needs the real background |
| `honest` ("closest-fit, not overclaiming") | 1.5 | ❌ needs the real background |
| `relevant` ("addresses the question") | 1.5 | ✅ focus is in the criterion |
| `specific` ("concrete projects/tech/metrics") | 1.0 | ⚠️ presence only, not truth |

Demonstrated: in the pre-`ingest_state` empty-context runs, the agent hallucinated (e.g. *"Snowflake and BigQuery"* — Matthew's real stack is Databricks/dbt) and the judge still scored `grounded` ~0.85. The gap persists in grounded runs too — a confident fabrication scores high. The brittle `mentions_X` deterministic checks were doing more real grounding-verification than the 2.0-weight `grounded` criterion.

## 2. Fix

Pass the reference into the judge and instruct it to score support, not plausibility:

```python
ref = (f"REFERENCE — the ONLY facts that count as grounded:\n{ctx.injected_knowledge}\n\n"
       if ctx.injected_knowledge else "")
prompt = ("Score each criterion 0–1. Treat any claim not supported by REFERENCE as a "
          "grounding/honesty failure (a fabricated-but-fluent claim must score LOW).\n\n"
          f"{ref}RUBRIC:\n{items}\n\nARTIFACT:\n{ctx.output}\n")
```

Keep the existing per-rubric `json_schema` structured output. Apply the same change to the Claude judge for parity. When `injected_knowledge` is empty (no reference available), omit the REFERENCE block and the judge degrades to today's behavior — no regression for non-grounded cases.

## 3. Why now (dependency)

This was **impossible before this session's work**: pre-`ingest_state`, `injected_knowledge` was empty, so there'd be nothing to check against. The chain is `ingest_state: active` (facts reach the prompt) → `reader: retrieving, top_k=0` (a *focused, relevant* reference, not an 11.9k-char dump) → **grounding-aware judge feasible and cheap**.

## 4. Payoff

- `grounded`/`honest` scores finally track reality (catch fabrication; the empty-context hallucination would score low).
- Lets us **retire or de-weight the brittle `mentions_X` keyword checks** — semantic support-verification replaces literal-token matching, ending the model/phrasing lottery (e.g. an answer that says "retrieval-augmented generation" no longer fails `(?i)rag`).
- Makes the application suite a **reliable** FR-030/SC-013 regression instrument rather than a phrasing-sensitive one.

## 5. Risks & open questions

- **Reference size / cost:** feeding the whole graph is wasteful; the `top_k=0` retrieving reader already trims it to the relevant subset — use `ctx.injected_knowledge` as-is.
- **Judge nondeterminism:** the judge is still a live LLM, so scores wobble run-to-run; a reference-aware judge is *more* stable than literal-token checks but not deterministic. Consider a verdict-cassette over the judge (like merge/conflict) if reproducibility is needed.
- **Validation:** re-run the application suite; confirm (a) genuinely ungrounded answers now score low on `grounded`/`honest`, and (b) the keyword checks become redundant before removing them.
- **Out of scope:** changing the rubric criteria themselves; making the agent deterministic.
