---
name: whats-next-monica
description: Recommend Monica's next dashboard/human-gate pillar task by checking the sprint plan, gap checklist, and current branch state.
---

# What's next for Monica?

Answer the recurring "what should I work on next for my pillar?" question with a
short, ranked, grounded recommendation — not a generic plan.

## Gather (read, don't guess)

1. **Sprint truth + gaps:** `README.md` (Sprint TODO block) and
   `docs/monica/PLAN_ALIGNMENT_GAP_CHECKLIST.md` — find unchecked Monica items and
   today's sprint day.
2. **Branch state:** `git fetch origin main`; `git status`; `git log origin/main..HEAD`
   — note unmerged work, WIP, or anything behind `main`.
3. **Pillar scope:** Monica = dashboard & human gate (`frontend-react/`, `frontend/`),
   docs in `docs/monica/`. Honor `.cursor/rules/praxis-dashboard.mdc` and
   `praxis-guardrails.mdc` (stay out of Matthew/Dominic work).

## Recommend

Return **3–5 ranked next tasks**, each with:

- **What** — one concrete deliverable.
- **Why now** — tie to sprint day, a P0/demo gate, or an open gap-checklist item.
- **Scope check** — confirm it's Monica-only and won't block teammates (mock/stub
  if it needs teammate behavior).
- **Definition of done** — the test/build/doc that proves it.

Lead with the single highest-leverage item for the nearest milestone (integration,
feature freeze, or a demo practice gate). Don't start implementing — wait for the
user to pick one, then use `/implement-plan`.
