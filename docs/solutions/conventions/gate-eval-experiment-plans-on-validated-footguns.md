---
title: Gate eval-experiment plans on empirically-validated footguns, not re-derived ones
date: 2026-06-24
category: conventions
module: knowledge/evals (PR-knowledge experiments)
problem_type: convention
component: development_workflow
severity: medium
related_components: [testing_framework]
applies_when:
  - Authoring or reviewing a plan for an eval/A-B experiment that reuses constructs from a sibling experiment
  - A measurement construct (footgun, fixture, metric) has already been run empirically in a related suite
  - About to spend real agent-run budget to validate a hypothesis
tags: [eval-harness, footgun, experiment-design, measurement-validity, dogfood, knowledge-injection, planning]
---

# Gate eval-experiment plans on empirically-validated footguns, not re-derived ones

## Context

We had just finished a dogfood experiment (`knowledge/evals/cases/dom/pr_knowledge_dogfood/`, see its
`RESULTS.md`) that empirically tested whether injected knowledge helps a coding agent avoid "footguns"
— tasks whose blind default is a documented gotcha. The v2 run produced hard validity data on each
construct:

- **`yoyo_lazy_import`** (`1fdb8be`/#48) — the **only** reliably blind-tempting footgun: the no-facts
  control hit it **3/3** (a top-level `from knowledge...` import that fails under yoyo's loader),
  treatment avoided 3/3, clean flip.
- **`phoenix_tracing`** (`22db05f`) — **invalid**: the control never exhibited the footgun (**0/3**),
  so there was nothing to flip. Removed in v2.
- **`umap_neighbors`** (`d892e88`/#57) — **variance-prone**: control exhibited it 2/3 in v1 but
  **0/3** in v2. At n≈3 its flip is a coin-flip. Demoted to a non-gating cost signal.

A sibling plan — `docs/plans/2026-06-24-002-feat-pr-knowledge-auto-distill-plan.md` — had been written
"independently" of that run, and it named its two gating footguns as `umap_neighbors` **and**
`phoenix_tracing`: precisely the two the dogfood run had just proven weak and invalid. The validated
construct, `yoyo_lazy_import`, was not in the plan at all. Running `/ce-work` on it as written would
have spent a multi-dollar real-agent run (3 arms × ~3 trials) re-discovering that those constructs
don't measure anything — an apparatus-attributed null, not a knowledge-value finding.

## Guidance

When a plan's measurement constructs were already exercised empirically by a sibling experiment, **carry
forward the validated ones and drop/demote the falsified ones before spending real budget.** Cross-check
the plan's constructs against the prior run's `RESULTS.md` (the empirical exhibit/flip rates), not
against the plan's own pre-validation construct list or its internally-reasoned "this one looks
stronger" claims.

Concretely, the fix was a `/ce-plan` revision of the offending unit (U4) and every downstream reference:

- **Swap in** `yoyo_lazy_import` as the gating footgun (copy the validated case verbatim from the
  dogfood suite, changing only the seed source).
- **Demote** `umap_neighbors` to a non-gating cost signal — keep it for its token/turn flailing signal,
  stop gating on its flip.
- **Drop** `phoenix_tracing` entirely.
- **Record why** in a dated revision note inside the plan, and propagate the single-footgun risk into
  the Risks section (the dogfood lesson is to gate on ≥2 validated footguns; one is thinner than ideal,
  so the verdict must be reported as provisional).

## Why This Matters

Measurement validity is **empirical, not derivable from the plan text**. A plan can read as rigorous —
clear footgun mechanics, a stated "this construct is the stronger of the two" — and still rest entirely
on constructs a sibling run already falsified. The 002 plan even predicted phoenix was "weaker than
UMAP," yet had it backwards: phoenix was *invalid* and UMAP was the *less* reliable of the two. Only the
empirical run knew that.

Real-agent eval runs cost money and wall-clock. An **apparatus-attributed null is the most expensive
kind of null** because it teaches nothing about the actual hypothesis — you pay full price and learn
only that your instrument was broken. Catching the construct mismatch at plan-review time (a ~15-minute
edit) instead of after the run is a large, cheap save. This is the plan-authoring-stage application of
the n=3 footgun-variance lesson captured in the `knowledge-injection-cost-to-correct` auto-memory note
("gate on ≥2 reliably-blind-tempting footguns, not one").

## When to Apply

- Authoring or reviewing any eval/A-B experiment plan that reuses footguns, fixtures, or metrics from a
  prior suite.
- Immediately before `/ce-work` on such a plan, as a readiness gate.
- Whenever a plan claims to be built "independently" of a sibling experiment but shares its measurement
  apparatus — independence of *implementation* does not grant independence from the sibling's *validity
  findings*.
- Before spending real agent-run (or any metered-LLM) budget to confirm a hypothesis.

## Examples

The before/after of the actual revision:

| Construct | Plan as written (before) | After cross-checking dogfood `RESULTS.md` |
|---|---|---|
| `yoyo_lazy_import` | absent | **gating footgun** (control 3/3 — validated) |
| `phoenix_tracing` | gating footgun (3 arms) | **dropped** (control 0/3 — invalid) |
| `umap_neighbors` | gating footgun ("the stronger one") | **demoted** to non-gating cost signal (2/3 → 0/3 — variance-prone) |

The tell that triggered the catch: the plan's two footguns were *exactly* the two a just-completed
sibling run had flagged as problematic, and the one construct that run validated was missing. Whenever a
downstream plan's apparatus is a near-copy of an experiment you already ran, diff it against that
experiment's results table before executing.

## Related

- Dogfood experiment suite + verdict: `knowledge/evals/cases/dom/pr_knowledge_dogfood/RESULTS.md`
- Revised plan: `docs/plans/2026-06-24-002-feat-pr-knowledge-auto-distill-plan.md` (see its
  "Revision (2026-06-24)" note and Risks section)
- Auto-memory: `knowledge-injection-cost-to-correct` (the n=3 footgun-variance lesson and cost-to-correct
  gating metric this convention operationalizes)
- Footgun source commits: `1fdb8be` (#48, yoyo lazy-import), `d892e88` (#57, UMAP n_neighbors),
  `22db05f` (Phoenix tracing at import — dropped)
