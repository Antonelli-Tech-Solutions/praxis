"""Regenerate the committed merge-verdict cassette for ``merge_model`` eval cases.

Run locally with ``OPENROUTER_API_KEY`` set. It re-runs every case that sets
``merge_model``, driving the ingestion/seed writes so the recording
``VerdictCassette`` captures the exact merge decisions those cases make at write time
(and, as a side effect, records any missing embedding vectors the recall gate needs).
Then commit the cassette + the embedding fixture.

    uv run python -m knowledge.evals.verdict_cache --refresh
"""

from __future__ import annotations

import argparse
import os
import sys

from knowledge.evals.run import _build_trio_for, load_cases, load_env


def refresh() -> int:
    if not os.getenv("OPENROUTER_API_KEY"):
        print(
            "set OPENROUTER_API_KEY (+ OPENROUTER_EMBED_MODEL) to refresh the cassette",
            file=sys.stderr,
        )
        return 1

    cases = [c for c in load_cases() if c.merge_model]
    if not cases:
        print("no `merge_model` cases to record")
        return 0

    for case in cases:
        # Seeding drives graph.write -> Deduper -> MergeJudge, so the recording
        # cassette captures each merge verdict (and the embed cache captures misses).
        graph, ingestor, _ = _build_trio_for(case)
        for text in case.seeded_insight.direct_to_graph:
            graph.write(text)
        for text in case.seeded_insight.via_ingestor:
            ingestor.ingest(text)
        print(f"recorded {case.id}")

    print(f"wrote merge verdicts for {len(cases)} case(s)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="knowledge.evals.verdict_cache")
    parser.add_argument(
        "--refresh", action="store_true", help="record merge verdicts for merge_model cases"
    )
    args = parser.parse_args(argv)
    if not args.refresh:
        parser.print_help()
        return 0
    load_env()
    return refresh()


if __name__ == "__main__":
    main()
