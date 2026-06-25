"""U3: one-shot backfill — distill the last N merged PRs (+ named commits) into a
frozen fact artifact the eval suite seeds from.

The **live** run (real ``gh`` + real ``Llm``) is a MANUAL one-shot the implementer
runs once to produce two committed artifacts:

  - ``facts.frozen.txt``     — the distilled fact texts (the seed-source snapshot)
  - ``facts.insights.json``  — full ``Insight`` metadata (source/scope/category) for R7

The eval suite and its tests depend on those committed artifacts thereafter, never
on re-distilling (KTD: freeze, keep distillation out of the eval loop — gpt-4o-mini
is not byte-stable even at temp 0). The core :func:`backfill` is fetcher- and
ingestor-injected so tests exercise it offline with fakes.

After running this, refresh the embedding cache for the new fact texts — every
frozen fact is a guaranteed cache miss, and ``CachedEmbedder.embed`` raises on a
miss with no API key, so the U4 treatment cases would error offline without
committed vectors::

    python -m knowledge.injestion.backfill_prs 30        # live: writes the artifacts
    python -m knowledge.evals.embed_cache --refresh      # live: re-embeds + commits cache
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from knowledge.injestion.injestion_def import Insight
from knowledge.injestion.parent_injestor import Ingestor
from knowledge.injestion.pr_source import (
    Fetcher,
    build_commit_document,
    build_pr_document,
    default_fetcher,
    list_merged_prs,
)

# Where the committed artifacts land (the new eval suite folder). backfill_prs.py
# lives in knowledge/injestion/, so parents[1] is knowledge/.
ARTIFACT_DIR = (
    Path(__file__).resolve().parents[1]
    / "evals" / "cases" / "dom" / "pr_knowledge_autodistill"
)

# Footgun-neutralizing facts must be in the frozen set even if their PR is older than
# the backfill window. These landed as single-parent commits with extractable diffs:
#   1fdb8be = yoyo lazy-import (the GATING footgun, dogfood-validated 3/3)
#   d892e88 = UMAP n_neighbors (the demoted non-gating cost signal)
FOOTGUN_COMMITS = ("1fdb8be", "d892e88")


def backfill(
    *,
    ingestor: Ingestor,
    fetch: Fetcher = default_fetcher,
    pr_limit: int = 30,
    commit_shas: tuple[str, ...] = (),
) -> list[Insight]:
    """Distill the last ``pr_limit`` merged PRs plus each commit in ``commit_shas``.

    Calls ``ingestor.synthesis`` directly (graph-free) and de-duplicates exact-text
    repeats, preserving first-seen order so the artifacts serialize deterministically.
    A single unit whose fetch or distill fails is skipped with a warning rather than
    aborting the whole one-shot (a real backfill spans ~30 live PRs).
    """
    units: list[tuple[str, ...]] = [("pr", str(n)) for n in list_merged_prs(pr_limit, fetch=fetch)]
    units += [("commit", sha) for sha in commit_shas]

    insights: list[Insight] = []
    seen: set[str] = set()
    skipped = 0
    for kind, ref in units:
        try:
            doc = (build_pr_document(int(ref), fetch=fetch) if kind == "pr"
                   else build_commit_document(ref, fetch=fetch))
            distilled = ingestor.synthesis(doc.render(), source=doc.unit_source)
        except Exception as exc:  # noqa: BLE001 — one bad unit shouldn't sink the backfill
            skipped += 1
            print(f"  WARN: skipping {kind}:{ref} — {type(exc).__name__}: {exc}", flush=True)
            continue
        for ins in distilled:
            key = ins.raw_text.strip()
            if key and key not in seen:
                seen.add(key)
                insights.append(ins)
    if skipped:
        # Surface mass-skip (e.g. a code bug hitting every unit) before artifacts are frozen.
        print(f"  NOTE: {skipped}/{len(units)} units skipped — review WARN lines above", flush=True)
    return insights


def serialize_facts(insights: list[Insight]) -> str:
    """The ``facts.frozen.txt`` snapshot: one fact per line (internal whitespace collapsed)."""
    return "".join(" ".join(i.raw_text.split()) + "\n" for i in insights)


def serialize_insights(insights: list[Insight]) -> str:
    """The ``facts.insights.json`` record: full metadata for R7 diagnostics."""
    return json.dumps([i.model_dump() for i in insights], indent=2, ensure_ascii=False) + "\n"


def write_artifacts(insights: list[Insight], out_dir: Path = ARTIFACT_DIR) -> None:
    """Write both committed artifacts deterministically."""
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "facts.frozen.txt").write_text(serialize_facts(insights), encoding="utf-8")
    (out_dir / "facts.insights.json").write_text(serialize_insights(insights), encoding="utf-8")


def main(pr_limit: int = 30) -> None:  # pragma: no cover — live one-shot
    """LIVE backfill: real ``gh`` fetch + real distill. Needs gh auth + OPENROUTER_API_KEY."""
    from knowledge.injestion.injestor_variants.commit_injestor import CommitIngestor
    from knowledge.knowledge_graph.knowledge_graph_variants.in_memory_graph import InMemoryGraph
    from knowledge.llm.llm_variants.openrouter_llm import OpenRouterLlm

    ingestor = CommitIngestor(InMemoryGraph(), OpenRouterLlm())
    insights = backfill(ingestor=ingestor, pr_limit=pr_limit, commit_shas=FOOTGUN_COMMITS)
    write_artifacts(insights)
    print(f"wrote {len(insights)} distilled facts to {ARTIFACT_DIR}")
    print("next: python -m knowledge.evals.embed_cache --refresh   # re-embed + commit cache")


if __name__ == "__main__":  # pragma: no cover
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 30)
