---
name: ship
description: Sync, test, commit, and push PRAXIS dev work to the dual GitHub+GitLab remote (and open an MR when asked).
---

# Ship it

Follow the project skill at `.cursor/skills/ship-praxis-work/SKILL.md`.

## Quick steps

1. Sync dev branch with main (`/sync-with-main`).
2. Run the tests relevant to what changed; fix failures.
3. `git status` / `git diff` — stage only task-relevant files (include exported
   fixtures if data changed).
4. Conventional commit (`feat|fix|docs|chore(scope): ...`), PowerShell `-m`/here-string.
5. `git push origin monica/dashboard-human-gate` (updates GitHub **and** GitLab).
6. Verify both remote refs match HEAD; open an MR targeting `main` only if asked.

Never push dev → `main` directly. PowerShell: use `;` not `&&`.
