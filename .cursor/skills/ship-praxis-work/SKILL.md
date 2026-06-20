---
name: ship-praxis-work
description: Ship PRAXIS dev work — sync with GitLab main, run tests, make a conventional commit, push to the dual GitHub+GitLab remote, verify both, and optionally open an MR to main. Use when the user says git add/commit/push, "push to both", ship, publish my branch, or open an MR.
---

# Ship PRAXIS work

The recurring end-of-task loop: get current, prove green, commit cleanly, push to
**both** remotes, and (when asked) open an MR. Default dev branch:
`monica/dashboard-human-gate`.

## Key facts

- **`origin` is dual-remote:** `fetch` = GitLab; `push` = GitHub **and** GitLab.
  A single `git push origin <branch>` updates both. After pushing, confirm both
  remote refs match local HEAD when the user asks "is it on GitHub/GitLab too?".
- **Sync direction is always `origin/main` → dev branch.** Never push dev → main;
  merge to `main` only via an MR. See `.cursor/rules/praxis-git-sync.mdc`.
- **PowerShell:** chain with `;` not `&&`. Multi-line commit messages use repeated
  `-m` flags or a here-string, not bash `$(cat <<EOF)`. Git progress on stderr is
  not an error.

## Workflow

Copy and track:

```
- [ ] 1. Sync dev branch with main
- [ ] 2. Run relevant tests (prove green)
- [ ] 3. Stage only task-relevant files
- [ ] 4. Conventional commit
- [ ] 5. Push to dual remote
- [ ] 6. Verify both remotes (and open MR if asked)
```

### 1. Sync first

Follow `.cursor/skills/sync-dev-with-gitlab-main/SKILL.md` (or `/sync-with-main`):

```powershell
git fetch origin main; git merge origin/main
```

Resolve conflicts on the dev branch only. Never on `main`.

### 2. Run tests for what changed

```powershell
# React dashboard
cd frontend-react; npm test; npm run lint; npm run build
# Python contract / mock alignment
uv run pytest frontend/tests/ -q
# Eval case registry (if cases changed)
uv run pytest knowledge/evals/tests/test_cases.py -q
```

Only run the suites relevant to the change. Fix failures before committing.

### 3. Stage selectively

`git status` / `git diff` first. Stage only files for this task — don't sweep up
unrelated untracked docs. If the user did data work, make sure exported fixtures
are staged (see `praxis-mock-eval-export`); stale committed fixtures are a
recurring bug.

### 4. Conventional commit

`feat|fix|chore|docs|refactor|test(scope): summary`, scope usually `dashboard`.
Use a HEREDOC-style here-string in PowerShell:

```powershell
git commit -m "feat(dashboard): add live/mock data source toggle" -m "Why: ..."
```

### 5. Push (hits GitHub + GitLab)

```powershell
git push origin monica/dashboard-human-gate
```

### 6. Verify / MR

- Verify: `git log origin/monica/dashboard-human-gate -1 --oneline` matches HEAD.
- MR only when asked. Sync with main first (step 1), simulate-merge mentally for
  conflicts, then open the MR **targeting `main`** with an enterprise-quality
  description (summary, why, test plan). If the GitLab MCP is unauthenticated,
  fall back to `git push origin <branch> -o merge_request.create` or hand the user
  a prefilled MR URL + description. Do not merge to `main` locally.

## Guardrails

- Never commit secrets (`.env`, tokens, AWS keys). Secrets are environment-only.
- Don't commit Office lock files (`~$*.docx`) — they belong in `.gitignore`.
- Stay within Monica's pillar; don't stage teammate-owned files
  (`.cursor/rules/praxis-guardrails.mdc`).
