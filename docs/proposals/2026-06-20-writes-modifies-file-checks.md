# Proposal: faithful per-artifact grading (`output_file` + `writes_file` / `modifies_file`)

**Owner:** Dominic Antonelli — eval harness
**Status:** Draft — for review
**Date:** 2026-06-20
**Scope:** `knowledge/evals` (EvalCase + EvalContext contracts, ClaudeCodeRunner, deterministic checks)

> Two related changes that make sandbox grading read the *agent's artifact*, not
> whatever blob the runner happened to assemble: **`output_file`** scopes the
> graded *content* to one file (§4.5); **`writes_file` / `modifies_file`** assert a
> file's *existence / change* (§4.1–4.4). They compose: one says *which file's
> content to grade*, the other says *that the agent produced it*.

---

## 1. Problem

Every full-pipeline case grades a blob of text. In sandbox mode that blob is the
file the agent wrote; in single-shot mode it's the chat reply. Our deterministic
checks (`contains_text`, the indentation regexes, the `os.path`/`pathlib`
substring checks, the AST `function_calls`) all read that blob **without caring
where it came from**. Consequences:

- A chatty reply that *talks about* the answer passes the same substring checks as
  a real artifact. `defines_add: contains_text "def add"` is green whether the
  agent wrote `def add` into `calculator.py` or merely typed it in a chat message.
- When the agent never writes the expected file, `ClaudeCodeRunner` silently falls
  back to a box-sweep or the assistant's final text
  (`_collect_output`, [claude_code.py:226-253](../../knowledge/evals/claude_code.py)),
  so "no artifact produced" is **not** distinguishable from "correct artifact
  produced" at grading time.
- **The box-sweep grades the fixture too.** For a code case the runner can't find
  its single configured `output_file` (`poem.txt`), so it falls back to a sweep
  that concatenates *every* file in the box — including the mounted fixture. A
  check meant to grade `answer.py` actually reads `answer.py` + `utils.py` + …, so
  the fixture's own content can satisfy (or break) the check.

Nothing in the suite asserts *the agent actually wrote (or modified) the file the
case is about*, and content checks can't scope to *just that file*. This proposal
adds:

- `output_file` (per-case) — grade the *content* of one named artifact, not the
  whole box (§4.5).
- `writes_file(path)` — the agent **created** a new file at `path` (§4.3).
- `modifies_file(path)` — the agent **changed** a file that was mounted at `path` (§4.3).

## 2. The constraint that shapes the design

The box is a `tempfile.TemporaryDirectory` whose `return EvalContext(...)` happens
**inside** the `with` block
([claude_code.py:174-224](../../knowledge/evals/claude_code.py)). The directory is
deleted as `run()` returns — *before* `run_case_full` calls `run_checks`. So a
check **cannot** stat the filesystem post-hoc; the box no longer exists.

Therefore the artifact signal must be **captured during the run and carried on
`EvalContext`**. Checks then read that captured data, not the disk.

`EvalContext` already carries `output_source` (`named_file` | `box_sweep` |
`final_text` | `completion`) and `checkout_path`, but `output_source="named_file"`
only tracks the runner's *single* configured `output_file` (default `poem.txt`) —
it can't speak to an arbitrary per-case filename, and it can't distinguish
*created* from *modified*. So we need a new, richer field.

## 3. Goals / non-goals

**Goals**
- Assert that a specific file was created / modified by the agent, faithfully.
- Scope *content* checks to the artifact under test, not the whole box (fixtures
  included).
- Distinguish "produced the artifact" from "talked about it in chat."
- Keep default behavior unchanged — both pieces are opt-in per case; cases that
  set neither grade exactly as today.
- Stay offline-testable (CLI is already injected).

**Non-goals**
- No content assertions here — `writes_file` says *the file exists/changed*, not
  *what's in it*. Content is still the job of `contains_text`, the regexes, etc.
- No per-check capability gating. "Sandbox only" is expressed at the **case**
  level via `needs: [sandbox]` (see §6).
- No change to the single-shot or fake backends' behavior.

## 4. Design

### 4.1 New contract field

```python
# knowledge/evals/eval_def.py
class Artifact(BaseModel):
    path: str                                  # box-relative, posix ("calculator.py")
    status: Literal["created", "modified"]     # vs the mounted start state

class EvalContext(BaseModel):
    ...
    artifacts: list[Artifact] = Field(default_factory=list)  # files the agent produced/changed
```

Backward compatible: optional, defaults empty. A runner with nothing to report
(`FakeRunner`, `OpenRouterRunner`) leaves it `[]`.

### 4.2 Runner populates it (ClaudeCodeRunner only)

`ClaudeCodeRunner.run` already mounts fixtures, runs the agent, then collects
output. We insert a **snapshot before** the agent runs and a **diff after**:

1. After mounting (`mount_fixtures` + `fixture_path` copytree), walk the box and
   record `start = {relpath: sha256(bytes)}` for every file. This is the start
   state the agent will edit.
2. After `run_cli`, walk the box again → `end = {relpath: sha256(bytes)}`.
3. For each path in `end`:
   - not in `start` → `Artifact(path, "created")`
   - in `start`, hash differs → `Artifact(path, "modified")`
   - hash equal → omit (unchanged)
4. Attach the list to the returned `EvalContext`.

Notes:
- Hash **raw bytes**, so binary files and unreadable files still diff correctly
  (detection doesn't need to decode them, unlike the text sweep that builds `output`).
- Skip dotfile paths (`.git`, etc.), matching the existing sweep's convention.
- This is independent of which blob becomes `output`; `_collect_output` is
  unchanged. Artifacts is pure provenance alongside it.

### 4.3 The checks

```python
# knowledge/evals/deterministic_checks/builds.py
def writes_file(ctx, *, path: str) -> CheckResult:
    """Pass iff the agent CREATED a new file at `path` (box-relative)."""
    created = {a.path for a in ctx.artifacts if a.status == "created"}
    ok = path in created
    return CheckResult(name="writes_file", passed=ok, evidence=...)

def modifies_file(ctx, *, path: str) -> CheckResult:
    """Pass iff the agent MODIFIED an existing (mounted) file at `path`."""
    modified = {a.path for a in ctx.artifacts if a.status == "modified"}
    ok = path in modified
    return CheckResult(name="modifies_file", passed=ok, evidence=...)
```

Deliberately **non-overlapping**: `writes_file` = new, `modifies_file` =
changed-existing. (A future `touches_file` could mean "created OR modified" if a
case ever needs the union; not adding it speculatively.)

### 4.4 Semantics table

| File at `path` after the run | `writes_file` | `modifies_file` |
|------------------------------|:-------------:|:---------------:|
| created (wasn't in fixture)  | **pass**      | fail            |
| modified (was in fixture)    | fail          | **pass**        |
| unchanged (was in fixture)   | fail          | fail            |
| absent / never written       | fail          | fail            |
| runner records no artifacts (single-shot, fake) | fail | fail |

The last row is why these checks force a case onto the sandbox (§6).

### 4.5 Per-case `output_file` (content grading)

`writes_file`/`modifies_file` assert a file *exists/changed*; they say nothing
about its content. Content is still graded against `EvalContext.output` — and for
a code case `output` is the **box-sweep**, fixture and all (see §1). So a per-case
way to say "*grade this file's content*" is the other half of faithful grading.

Add an optional field to the **case**:

```python
# knowledge/evals/eval_def.py
class EvalCase(BaseModel):
    ...
    output_file: str | None = None  # box-relative artifact to grade; None => runner default
```

`ClaudeCodeRunner._collect_output` prefers `case.output_file` (when set) over the
runner's built-in default before falling back to the box-sweep. When set and the
file exists, `output` is *that file alone* and `output_source="named_file"`, so
every existing content check (`contains_text`, the regexes, `function_calls`)
scopes to the agent's artifact. If the file is absent, the existing fallback still
applies — and `writes_file` is what flags the absence.

**Measured motivation** (`fixture_reuse_existing_helper`, Haiku, neutral prompt):
with the reuse lesson the agent writes `from utils import slugify`; cold it
reimplements the slug inline. *Both arms currently PASS* `calls_slugify` and
`does_not_reimplement_slugify`, because the box-sweep includes the fixture's
`utils.py`, which itself contains `slugify(` and one `def slugify`. With
`output_file: answer.py` the checks read only the agent's file, and
`calls_slugify` becomes a clean reuse-vs-reimplement discriminator (reuse → the
call is present; inline reimplement → absent).

This composes with §4.1–4.4: `artifacts` says *which* files changed (existence);
`output_file` says *which file's content* to grade. A reuse-steering case wants
both — `writes_file(answer.py)` (the agent produced it) and `output_file: answer.py`
(grade its content).

## 5. Worked examples

- **`fixture_reuse_existing_helper`** (new file + content): the agent writes
  `answer.py`; the fixture ships `utils.py`. Set `output_file: answer.py` (so
  `calls_slugify` reads only the agent's file) **and** `writes_file(path: "answer.py")`
  (so an empty chat reply can't pass). This is the case that motivated the proposal
  — its current checks are fixture-contaminated (§4.5).
- **`iambic_poem`** (new file): add `writes_file(path: "poem.txt")` alongside the
  meter check. Now "wrote the poem to the file" is asserted, not assumed.
- **Edit-in-place case** (a fixture source file the agent must change): use
  `modifies_file(path: "<that file>")` to assert the edit landed — pair it with a
  content check (scoped via `output_file`) that asserts *how* it changed.

## 6. Capability gating

A case carrying `writes_file`/`modifies_file` only makes sense on a runner that
provides a sandbox; everywhere else `artifacts` is empty and the check fails.
Two ways to keep that honest:

- **Explicit (minimum):** author adds `needs: [sandbox]` to any case using these
  checks. Simple, no magic. Risk: forget it → the case FAILs on OpenRouter
  instead of SKIPping.
- **Auto-derive (recommended safeguard):** extend `case_needs`
  ([run.py:124-140](../../knowledge/evals/run.py)) to add `"sandbox"` when any
  deterministic check ref ends in `:writes_file` or `:modifies_file`. Removes the
  footgun at the cost of a small name-coupling in `case_needs`.

Recommendation: do the auto-derive — it's a few lines and prevents a whole class
of "phantom FAIL on the wrong backend" misconfig, consistent with the existing
fixtures→sandbox auto-derivation.

## 7. Implementation plan

1. `eval_def.py`: add `Artifact` model + `EvalContext.artifacts` (default empty),
   and `EvalCase.output_file` (default `None`).
2. `claude_code.py`: snapshot-after-mount, diff-after-run, attach artifacts; and
   have `_collect_output` honor `case.output_file` before the box-sweep fallback.
   Factor the box walk into a small `_hash_tree(workdir) -> dict[str, str]` helper.
3. `builds.py`: add `writes_file` + `modifies_file`.
4. `run.py`: extend `case_needs` to auto-derive `sandbox` for these checks (§6).
5. Adopt in cases: rework `fixture_reuse_existing_helper` (neutral prompt +
   `output_file: answer.py` + `writes_file` + a before-control), and add
   `writes_file` to `iambic_poem`. Others opt in case-by-case.
6. Tests (all offline).

## 8. Testing strategy

All offline via the injected `run_cli`. The fake CLI writes (or doesn't write)
files into the box, exactly as the existing
`test_runner_copies_fixture_into_box` does
([test_claude_code.py:72-91](../../knowledge/evals/tests/test_claude_code.py)).

- **Runner records created file**: fake CLI writes a new `answer.txt` →
  `ctx.artifacts == [Artifact("answer.txt", "created")]`.
- **Runner records modified file**: fixture has `calculator.py`; fake CLI appends
  to it → status `"modified"`.
- **Unchanged file is omitted**: fixture file the CLI doesn't touch → not in
  `artifacts`.
- **Check unit tests** (`test_builds.py`): `writes_file` pass on created / fail on
  modified, absent, and empty-artifacts; `modifies_file` mirror.
- **Gating**: a case with `writes_file` is partitioned as skipped under
  `OpenRouterRunner`/`FakeRunner` with reason `needs 'sandbox'`.
- **`output_file` scoping**: fixture ships `utils.py`; fake CLI writes `answer.py`.
  With `output_file: answer.py`, `ctx.output` is `answer.py`'s content only
  (`output_source="named_file"`) and a substring present only in `utils.py` is not
  matched; unset, the box-sweep includes both.

## 9. Risks & alternatives

- **Box-walk cost.** Negligible — per-case eval, a handful of files, hashed once
  before and once after.
- **Hashing vs mtime.** Hash is robust to "rewrote identical content" (correctly
  → unchanged) and to clock quirks; mtime would be cheaper but lie. Hash wins.
- **Alternative A — `graded_from_artifact` (free, coarse).** A check that passes
  iff `output_source in {named_file, box_sweep}`. Zero harness change, catches the
  pure-chat-reply case, but can't name the file or tell created from modified.
  Strictly weaker; rejected because the ask is "the *correct* file."
- **Alternative — keep the box alive until after checks.** Move check execution
  inside the box lifecycle so a check can stat disk. Larger blast radius (changes
  the run/grade ordering for *all* cases) for no extra capability over capturing
  artifacts. Rejected.
- **Name-coupling in `case_needs`** (auto-derive) is mild magic. Acceptable and
  mirrors the existing fixtures→sandbox rule; documented in the function.

## 10. Open questions

1. Should `modifies_file` also accept a freshly *created* file at `path` (i.e.
   "ensure it exists, however it got there")? Current proposal says no — keep the
   created/modified split crisp. Revisit if a case needs the union.
2. Do we want a `deletes_file(path)` for cases that assert cleanup? Out of scope;
   trivial to add later (path in `start` but not in `end`).
3. Should `artifacts` also flow into the verbose `RunTranscript` for debugging?
   Low cost, probably yes — fold into the transcript's `AgentRun`.
4. When `output_file` is set but the file is **absent**, fall back to the box-sweep
   (current behavior, with `writes_file` flagging the absence) or fail the content
   check loudly? Proposal: keep the fallback — `writes_file` is the existence
   assertion, content checks stay orthogonal.
