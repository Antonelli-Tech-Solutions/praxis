---
name: implement-plan
description: Execute an attached/created plan end-to-end without editing the plan file, reusing existing todos, and finishing every item.
---

# Implement the plan

The single most repeated PRAXIS workflow: the user attaches or names a plan and
expects it implemented to completion. Follow this ritual exactly.

## Non-negotiable rules

1. **Do NOT edit the plan file itself.** It is the spec, not a worklog.
2. **Do NOT recreate todos** if the plan already generated them — reuse the
   existing list. Only create todos if none exist yet.
3. **Mark each todo `in_progress`** before starting it and `completed` the moment
   it lands. Only one `in_progress` at a time.
4. **Don't stop until every todo is complete.** No early hand-back with "should I
   continue?" unless you hit a real blocker or a scope/destructive decision.
5. **Stay inside Monica's pillar.** Do not edit Matthew's or Dominic's code, docs,
   or plans (see `.cursor/rules/praxis-guardrails.mdc`). Mock/stub on Monica's
   side instead. Flag cross-team impact before touching shared files.

## Steps

1. Read the referenced plan in full (do not modify it).
2. Confirm the todo list exists; if the plan created todos, load them as-is.
3. Work top-to-bottom: implement → run the relevant tests/build → mark complete.
4. After substantive edits, run lint/type checks and fix anything you introduced.
5. When all todos are done, give a short summary of what shipped and what (if
   anything) was intentionally left out of scope.
6. Only commit/push/open an MR if the user asks — then use the `ship-praxis-work`
   skill (`/ship`).

## Quality bar

Enterprise / interview-demo quality. Preserve existing functionality (search,
filter, sort, promote/decay, keyboard nav) during any UI work. Keep provenance
and confidence rationale visible per `.cursor/rules/praxis-dashboard.mdc`.
