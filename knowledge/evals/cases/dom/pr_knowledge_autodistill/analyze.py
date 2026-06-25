"""Measurement + R7 diagnostics for the PR-knowledge auto-distill slice.

Two arms on every task (no-facts CONTROL vs auto-distilled+retrieved AUTO) plus a
third CURATED ceiling arm on the one gating footgun (``yoyo_lazy_import``). The gate
is **directional token/turn reduction + the gating footgun's flip**; any GO is
reported **provisional** (a single validated footgun is thinner than the >=2 the
dogfood lesson recommends).

When the auto arm misses the footgun, R7 attributes the shortfall three ways:
  - **EXTRACTION**       — the neutralizing fact is absent/garbled from the frozen artifact.
  - **RETRIEVAL**        — the fact is in the artifact but the reader didn't surface it
                            (the finding that motivates two-lane scope-aware retrieval).
  - **KNOWLEDGE-VALUE**  — the fact was present AND surfaced AND even the force-injected
                            curated ceiling failed to flip it (the bet is weak).
  - **EXTRACTION-QUALITY** — present + surfaced, auto missed, but the curated ideal flipped
                            it (the distilled phrasing was weaker than the ideal).

The pure functions (:func:`aggregate`, :func:`attribute_shortfall`,
:func:`neutralizing_fact_present`, :func:`fact_surfaced`, :func:`evaluate_gate`)
operate on plain records/text so they unit-test offline against fixtures. Live
orchestration runs the real ``ClaudeCodeRunner`` in-process via ``run_case_full``
(not the ``knowledge.evals.run`` CLI, which clobbers the committed baseline).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _ensure_repo_on_path() -> None:
    """Allow ``python <suite>/analyze.py`` (run-by-path) to import ``knowledge``."""
    for parent in HERE.parents:
        if (parent / "pyproject.toml").exists():
            if str(parent) not in sys.path:
                sys.path.insert(0, str(parent))
            return


_ensure_repo_on_path()

from knowledge.evals.analyze_utils import (  # noqa: E402
    EXHIBIT_BAR,
    fmt,
    mean_sd,
    measure,
    rate,
)

# Below this many trials on a gating task the flip is a coin-flip and a GO is not
# defensible — the gate downgrades to NO-GO (insufficient data) regardless of the flip.
MIN_GATING_TRIALS = 3

# The footgun-absence check (regex_absent) is applied uniformly to ALL arms so a
# "flip" is comparable across them: correct == footgun avoided. `marker_terms` are
# the substrings that identify this task's neutralizing fact for the R7 extraction
# (was it distilled into the artifact?) and retrieval (did the reader surface it?)
# diagnostics. `gating` marks the one footgun the verdict actually gates on.
TASKS: dict[str, dict] = {
    # Case ids are namespaced ("autodistill_*") because the harness's load_cases()
    # globs a single global case dir and de-dupes by id — bare "yoyo_lazy_import"
    # collides with the sibling dogfood suite and silently shadows this arm.
    "autodistill_yoyo_lazy_import": {
        "kind": "footgun",
        "gating": True,
        "correct_check": ("knowledge.evals.deterministic_checks.text:regex_absent",
                          {"pattern": r"(?m)^(?:from|import)\s+knowledge\b"}),
        "output_file": "0002_backfill_fact_source.py",
        # The distiller phrases the gotcha as "...not on sys.path, necessitating lazy
        # imports..."; these terms identify the neutralizing fact across its variants.
        "marker_terms": ["sys.path", "import"],
        "has_curated": True,
    },
    "autodistill_delete_active_guard": {
        "kind": "footgun",
        "gating": True,  # validated 3/3 blind (unguarded DELETE); see RESULTS.md
        # Footgun AVOIDED = deletion guarded to proposed/rejected (note: regex_MATCHES,
        # opposite polarity to yoyo's regex_absent — the footgun here is an OMITTED guard).
        "correct_check": ("knowledge.evals.deterministic_checks.text:regex_matches",
                          {"pattern": r"(?i)\b(proposed|rejected)\b"}),
        "output_file": "delete_fact.py",
        "marker_terms": ["delet", "rejected"],  # "Deletion ... 'rejected' states"
        "has_curated": True,
    },
    "autodistill_umap_neighbors": {
        "kind": "footgun",
        "gating": False,  # demoted to a non-gating cost signal (dogfood control 2/3 -> 0/3)
        "correct_check": ("knowledge.evals.deterministic_checks.text:regex_absent",
                          {"pattern": r"n_neighbors\s*=\s*(?:min\()?\s*15\b"}),
        "output_file": "clustering.py",
        "marker_terms": ["n_neighbors"],
        "has_curated": False,
    },
    # A non-footgun convention/quantitative task (its id finalized in U4) appends here
    # with kind="quantitative", gating=False, correct_check=None — it carries only the
    # token/turn cost signal.
}


def control_id(task: str) -> str:
    return f"{task}_before"


def curated_id(task: str) -> str:
    return f"{task}_curated"


# --------------------------------------------------------------------------- #
# Pure aggregation over per-trial records
# --------------------------------------------------------------------------- #
# A record is: {task, kind,
#   auto:    {cost, turns, tokens, correct|None},   # correct == footgun avoided
#   control: {cost, turns, tokens, correct|None},
#   curated: {cost, turns, tokens, correct|None} | None}   # gating task only

def _arm_means(trials: list[dict], arm: str) -> dict:
    costs = [t[arm]["cost"] for t in trials if t.get(arm) and t[arm]["cost"] is not None]
    toks = [float(t[arm]["tokens"]) for t in trials if t.get(arm) and t[arm]["tokens"] is not None]
    turns = [float(t[arm]["turns"]) for t in trials if t.get(arm) and t[arm]["turns"] is not None]
    cost_mean, cost_sd = mean_sd(costs)
    tok_mean, tok_sd = mean_sd(toks)
    turn_mean, _ = mean_sd(turns)
    return {"cost_mean": cost_mean, "cost_sd": cost_sd, "tokens_mean": tok_mean,
            "tokens_sd": tok_sd, "turns_mean": turn_mean}


def aggregate(records: list[dict], tasks: dict | None = None) -> dict:
    """Per-task per-arm means, token/turn deltas, and the footgun flip. Errors -> NO-GO."""
    tasks = tasks or TASKS
    by_task: dict[str, list[dict]] = {}
    for r in records:
        by_task.setdefault(r["task"], []).append(r)

    out: dict[str, dict] = {}
    errors: list[str] = []
    for task, cfg in tasks.items():
        trials = by_task.get(task, [])
        if not trials:
            errors.append(f"{task}: no trials")
            continue

        auto = _arm_means(trials, "auto")
        control = _arm_means(trials, "control")
        if auto["tokens_mean"] is None or control["tokens_mean"] is None:
            errors.append(f"{task}: missing token data in an arm")
            continue

        kind = cfg["kind"]
        is_footgun = kind == "footgun"
        auto_avoid_rate = rate([t["auto"]["correct"] for t in trials])
        control_correct_rate = rate([t["control"]["correct"] for t in trials])
        control_exhibit_rate = None if control_correct_rate is None else 1.0 - control_correct_rate
        flip = bool(
            is_footgun and auto_avoid_rate is not None and control_exhibit_rate is not None
            and auto_avoid_rate >= 0.5 and control_exhibit_rate >= EXHIBIT_BAR
        )

        curated_trials = [t for t in trials if t.get("curated")]
        curated = _arm_means(curated_trials, "curated") if curated_trials else None
        curated_avoid_rate = (
            rate([t["curated"]["correct"] for t in curated_trials]) if curated_trials else None
        )
        curated_flip = None if curated_avoid_rate is None else curated_avoid_rate >= 0.5

        token_delta = auto["tokens_mean"] - control["tokens_mean"]  # negative => auto cheaper
        turn_delta = (
            None if auto["turns_mean"] is None or control["turns_mean"] is None
            else auto["turns_mean"] - control["turns_mean"]
        )
        out[task] = {
            "kind": kind,
            "is_footgun": is_footgun,
            "is_gating": bool(cfg.get("gating")),
            "auto": auto,
            "control": control,
            "curated": curated,
            "token_delta": token_delta,
            "token_reduced": auto["tokens_mean"] < control["tokens_mean"],
            "turn_delta": turn_delta,
            "turn_reduced": bool(turn_delta is not None and turn_delta < 0),
            "auto_avoid_rate": auto_avoid_rate,
            "control_exhibit_rate": control_exhibit_rate,
            "curated_avoid_rate": curated_avoid_rate,
            "flip": flip,
            "curated_flip": curated_flip,
            "trials": len(trials),
        }
    return {"tasks": out, "errors": errors}


# --------------------------------------------------------------------------- #
# R7 diagnostics (pure) — extraction + retrieval presence checks
# --------------------------------------------------------------------------- #

def neutralizing_fact_present(insights: list[dict], marker_terms: list[str]) -> bool:
    """True iff some distilled insight's text contains every marker term (case-insensitive).

    The extraction-side R7 signal: was the footgun-neutralizing fact actually
    distilled into the frozen artifact at all?
    """
    terms = [t.lower() for t in marker_terms]
    return any(
        all(term in str(i.get("raw_text", "")).lower() for term in terms)
        for i in insights
    )


def fact_surfaced(reader_output: str, marker_terms: list[str]) -> bool:
    """True iff the reader-injected text contains every marker term (case-insensitive).

    The retrieval-side R7 signal: did the (ranked) reader actually surface the fact
    to the agent? ``reader_output`` is the auto run's ``injected_knowledge``.
    """
    text = (reader_output or "").lower()
    return all(t.lower() in text for t in marker_terms)


def attribute_shortfall(
    *, flip: bool, fact_in_artifact: bool, surfaced: bool, curated_flip: bool | None
) -> str | None:
    """Attribute a gating-footgun shortfall. ``None`` when the auto arm flipped (a win)."""
    if flip:
        return None  # auto arm avoided the footgun — no shortfall to attribute
    if not fact_in_artifact:
        return "EXTRACTION"
    if not surfaced:
        return "RETRIEVAL"
    # present AND surfaced, auto still missed -> the curated ceiling splits the last two
    if curated_flip is None:
        return "KNOWLEDGE-VALUE"  # no curated arm to consult: default to the weaker-bet read
    return "EXTRACTION-QUALITY" if curated_flip else "KNOWLEDGE-VALUE"


# --------------------------------------------------------------------------- #
# Gate
# --------------------------------------------------------------------------- #

def evaluate_gate(report: dict) -> dict:
    """GO (provisional) iff the gating footgun flips AND auto cuts token/turn on a majority."""
    tasks, errors = report["tasks"], list(report["errors"])
    gating = [n for n, t in tasks.items() if t["is_gating"]]
    gating_flip = bool(gating) and all(tasks[n]["flip"] for n in gating)

    # A flip is a coin-flip at tiny n; the EXHIBIT_BAR (2/3) is only honest at n>=3.
    # Refuse a GO when any gating task ran too few trials — otherwise a 1-trial
    # --from-records blob or `--trials 1` prints a confident GO the data can't support.
    underpowered = [n for n in gating if tasks[n]["trials"] < MIN_GATING_TRIALS]

    reduced = {n: (t["token_reduced"] or t["turn_reduced"]) for n, t in tasks.items()}
    n_reduced = sum(reduced.values())
    most_reduced = bool(tasks) and n_reduced > len(tasks) / 2

    go = gating_flip and most_reduced and not underpowered and not errors
    reasons: list[str] = []
    if not gating:
        reasons.append("no gating footgun task present")
    if gating and not gating_flip:
        reasons.append("gating footgun did not flip: "
                       + ", ".join(n for n in gating if not tasks[n]["flip"]))
    if underpowered:
        reasons.append(f"gating task(s) under {MIN_GATING_TRIALS} trials (insufficient data): "
                       + ", ".join(f"{n}={tasks[n]['trials']}" for n in underpowered))
    if not most_reduced:
        reasons.append(f"token/turn reduced on only {n_reduced}/{len(tasks)} tasks (need a majority)")
    if errors:
        reasons.append("data errors: " + "; ".join(errors))

    # Even a clean GO is provisional: the upstream "does knowledge help at all" dogfood
    # premise is unestablished, and (at n=3) flips remain noisy.
    provisional_note = (f"GO is PROVISIONAL — {len(gating)} validated gating footgun(s), but the "
                        "dogfood 'does knowledge help' premise is unestablished and n=3; see RESULTS.md")
    return {
        "verdict": "GO (provisional)" if go else "NO-GO",
        "provisional": go,
        "gating_flip": gating_flip,
        "flips": {n: tasks[n]["flip"] for n in gating},
        "tasks_reduced": n_reduced,
        "tasks_total": len(tasks),
        "reasons": [provisional_note] if go else reasons,
    }


# --------------------------------------------------------------------------- #
# Live orchestration (real Claude Code, in-process) — exercised by U6
# --------------------------------------------------------------------------- #

def _load_insights() -> list[dict]:
    art = HERE / "facts.insights.json"
    if not art.exists():
        return []
    return json.loads(art.read_text(encoding="utf-8"))


def run_experiment(trials: int, tasks: dict | None = None) -> tuple[list[dict], dict]:
    """Run auto + control (+ curated on the gating task) for each task/trial.

    Returns ``(records, diagnostics)`` where diagnostics carries the R7 extraction +
    retrieval presence signals per task (extraction from the frozen artifact, retrieval
    from the auto run's injected_knowledge).
    """
    from knowledge.evals.run import load_cases, run_case_full, select_runner

    tasks = tasks or TASKS
    insights = _load_insights()
    if not insights:
        raise SystemExit(
            "facts.insights.json is missing/empty — run the live backfill first:\n"
            "  python -m knowledge.injestion.backfill_prs 30\n"
            "  python -m knowledge.evals.embed_cache --refresh"
        )
    cases = {c.id: c for c in load_cases()}
    # Fail fast if any arm's case id is absent (e.g. a rename drifted) rather than
    # KeyError-ing mid-run after spending on earlier trials.
    for task, cfg in tasks.items():
        needed = [task, control_id(task)] + ([curated_id(task)] if cfg.get("has_curated") else [])
        missing = [cid for cid in needed if cid not in cases]
        if missing:
            raise SystemExit(f"unknown case id(s) for task {task!r}: {missing} (author U4 cases first)")
    runner, judge = select_runner("claude")

    records: list[dict] = []
    diagnostics: dict[str, dict] = {}
    for task, cfg in tasks.items():
        check = cfg["correct_check"]
        markers = cfg.get("marker_terms", [])  # quantitative tasks carry none
        surfaced_count = 0
        for n in range(trials):
            actx, _, _ = run_case_full(cases[task], runner, judge=judge)
            auto = measure(actx, check)
            cctx, _, _ = run_case_full(cases[control_id(task)], runner, judge=judge)
            control = measure(cctx, check)
            curated = None
            if cfg.get("has_curated"):
                uctx, _, _ = run_case_full(cases[curated_id(task)], runner, judge=judge)
                curated = measure(uctx, check)
            if markers and fact_surfaced(getattr(actx, "injected_knowledge", "") or "", markers):
                surfaced_count += 1
            records.append({"task": task, "kind": cfg["kind"],
                            "auto": auto, "control": control, "curated": curated})
            print(f"  {task} trial {n + 1}/{trials}: auto_avoid={auto['correct']} "
                  f"ctrl_avoid={control['correct']} curated_avoid="
                  f"{curated['correct'] if curated else 'n/a'}", flush=True)
        diagnostics[task] = {
            "fact_in_artifact": bool(markers) and neutralizing_fact_present(insights, markers),
            # majority of trials, not any single one — an unstable retriever shouldn't read as surfaced
            "surfaced": bool(markers) and surfaced_count >= (trials / 2),
            "surfaced_trials": f"{surfaced_count}/{trials}",
        }
    return records, diagnostics


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #

def format_report(report: dict, gate: dict, diagnostics: dict | None = None) -> str:
    diagnostics = diagnostics or {}
    lines = ["=== PR-knowledge auto-distill — token/turn + footgun flip ===", ""]
    for task, t in report["tasks"].items():
        gate_tag = "GATING" if t["is_gating"] else ("cost-signal" if t["is_footgun"] else t["kind"])
        lines.append(f"[{task}] ({gate_tag}; {t['trials']} trials)")
        lines.append(
            f"  tokens  auto={fmt(t['auto']['tokens_mean'])}  control={fmt(t['control']['tokens_mean'])}  "
            f"delta={fmt(t['token_delta'])} ({'cheaper' if t['token_reduced'] else 'NOT cheaper'})"
        )
        lines.append(f"  turns   auto={fmt(t['auto']['turns_mean'])}  control={fmt(t['control']['turns_mean'])}")
        if t["is_footgun"]:
            lines.append(f"  footgun auto_avoid={fmt(t['auto_avoid_rate'])}  "
                         f"control_exhibit={fmt(t['control_exhibit_rate'])}  flip={t['flip']}"
                         + (f"  curated_flip={t['curated_flip']}" if t['curated'] is not None else ""))
            if t["is_gating"] and not t["flip"]:
                d = diagnostics.get(task, {})
                attribution = attribute_shortfall(
                    flip=t["flip"], fact_in_artifact=d.get("fact_in_artifact", False),
                    surfaced=d.get("surfaced", False), curated_flip=t["curated_flip"],
                )
                lines.append(f"  -> SHORTFALL ATTRIBUTED: {attribution}")
        lines.append("")
    if report["errors"]:
        lines.append("ERRORS: " + "; ".join(report["errors"]) + "\n")
    lines.append(f"VERDICT: {gate['verdict']}")
    for r in gate["reasons"]:
        lines.append(f"  - {r}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="analyze", description="auto-distill slice runner + gate")
    parser.add_argument("--trials", type=int, default=3, help="trials per task (default 3)")
    parser.add_argument("--from-records", type=Path, default=None,
                        help="aggregate a committed records JSON instead of running the agent")
    parser.add_argument("--out", type=Path, default=HERE / "RESULTS.data.json")
    args = parser.parse_args(argv)

    diagnostics: dict = {}
    if args.from_records is not None:
        blob = json.loads(args.from_records.read_text(encoding="utf-8"))
        records = blob["records"] if isinstance(blob, dict) else blob
        diagnostics = blob.get("diagnostics", {}) if isinstance(blob, dict) else {}
    else:
        print(f"running {len(TASKS)} tasks x {args.trials} trials (auto + control + curated) "
              "through real Claude Code...")
        records, diagnostics = run_experiment(args.trials)

    report = aggregate(records)
    gate = evaluate_gate(report)
    print("\n" + format_report(report, gate, diagnostics))

    if args.out is not None:
        args.out.write_text(
            json.dumps({"records": records, "diagnostics": diagnostics,
                        "report": report, "gate": gate}, indent=2),
            encoding="utf-8",
        )
        print(f"\nwrote results -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
