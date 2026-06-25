"""U3: offline tests for the backfill core + deterministic artifact serialization.

Drives :func:`backfill` with a fake fetcher (argv -> stdout) and a fake ingestor —
nothing shells out, nothing distills for real. Covers R3 (last-N listing) and the
freeze/dedup/determinism contract the committed artifacts depend on.
"""

from __future__ import annotations

import json

from knowledge.injestion.backfill_prs import (
    backfill,
    serialize_facts,
    serialize_insights,
    write_artifacts,
)
from knowledge.injestion.injestion_def import Insight


class FakeIngestor:
    """Returns scripted insights per unit source; records the sources it saw."""

    def __init__(self, by_source: dict[str, list[Insight]]) -> None:
        self.by_source = by_source
        self.seen: list[str] = []

    def synthesis(self, raw_input: str, *, source=None) -> list[Insight]:
        self.seen.append(source)
        return self.by_source.get(source, [])


def _pr_fetch(prs: dict[int, str], *, listed: list[int] | None = None):
    """Fake fetcher serving `gh pr list` + per-PR view/diff for the given PRs."""
    listed = listed if listed is not None else sorted(prs, reverse=True)

    def fetch(argv: list[str]) -> str:
        if argv[:3] == ["gh", "pr", "list"]:
            limit = int(argv[argv.index("--limit") + 1])
            return json.dumps([{"number": n, "state": "MERGED"} for n in listed[:limit]])
        if argv[:3] == ["gh", "pr", "view"]:
            n = int(argv[3])
            return json.dumps({"title": prs[n], "body": f"body {n}", "reviews": []})
        if argv[:3] == ["gh", "pr", "diff"]:
            n = int(argv[3])
            return f"diff --git a/f{n}.py b/f{n}.py\n+x"
        raise AssertionError(f"unexpected argv: {argv}")

    return fetch


def test_happy_path_writes_both_artifacts(tmp_path):
    # Covers the freeze contract: distilled facts -> facts.frozen.txt + facts.insights.json.
    ingestor = FakeIngestor({
        "git/pr:3": [Insight(raw_text="Fact A.", source="git/pr:3", scope="repo", category="gotcha")],
        "git/pr:2": [Insight(raw_text="Fact B.", source="git/pr:2", scope="module:x", category="decision")],
        "git/pr:1": [],
    })
    insights = backfill(ingestor=ingestor, fetch=_pr_fetch({1: "a", 2: "b", 3: "c"}), pr_limit=30)

    write_artifacts(insights, tmp_path)
    facts = (tmp_path / "facts.frozen.txt").read_text(encoding="utf-8")
    records = json.loads((tmp_path / "facts.insights.json").read_text(encoding="utf-8"))

    assert facts == "Fact A.\nFact B.\n"
    assert [r["raw_text"] for r in records] == ["Fact A.", "Fact B."]
    assert records[0]["source"] == "git/pr:3" and records[0]["category"] == "gotcha"


def test_listing_caps_at_limit_and_handles_short_history():
    # Covers R3: cap at N; asking for more PRs than exist stops cleanly.
    ingestor = FakeIngestor({f"git/pr:{n}": [Insight(raw_text=f"F{n}")] for n in (1, 2)})
    insights = backfill(ingestor=ingestor, fetch=_pr_fetch({1: "a", 2: "b"}), pr_limit=30)

    assert ingestor.seen == ["git/pr:2", "git/pr:1"]  # only the 2 that exist, newest first
    assert {i.raw_text for i in insights} == {"F1", "F2"}


def test_empty_distill_contributes_nothing_and_dedups():
    # Edge: a PR that distills to [] adds nothing; an exact-text repeat is dropped once.
    dup = Insight(raw_text="Same fact.", source="git/pr:2")
    ingestor = FakeIngestor({
        "git/pr:2": [dup],
        "git/pr:1": [Insight(raw_text="Same fact.", source="git/pr:1")],  # exact repeat
    })
    insights = backfill(ingestor=ingestor, fetch=_pr_fetch({1: "a", 2: "b"}), pr_limit=30)

    assert [i.raw_text for i in insights] == ["Same fact."]  # deduped to one


def test_one_failing_unit_is_skipped_not_fatal():
    # The "one bad unit shouldn't sink the backfill" contract: a fetch that raises
    # for PR 2 is skipped with a warning; PR 1 still contributes.
    ingestor = FakeIngestor({"git/pr:1": [Insight(raw_text="F1", source="git/pr:1")]})

    def fetch(argv):
        if argv[:3] == ["gh", "pr", "list"]:
            return json.dumps([{"number": 2, "state": "MERGED"}, {"number": 1, "state": "MERGED"}])
        if argv[:4] == ["gh", "pr", "view", "2"]:
            raise RuntimeError("boom: PR 2 fetch failed")
        if argv[:3] == ["gh", "pr", "view"]:
            return json.dumps({"title": "t", "body": "b", "reviews": []})
        if argv[:3] == ["gh", "pr", "diff"]:
            return "diff --git a/f.py b/f.py\n+x"
        raise AssertionError(argv)

    insights = backfill(ingestor=ingestor, fetch=fetch, pr_limit=30)
    assert [i.raw_text for i in insights] == ["F1"]  # PR 2 skipped, PR 1 survived


def test_serialization_is_byte_identical_for_same_inputs():
    # Determinism: same insights -> byte-identical artifacts (stable ordering, no clock).
    insights = [
        Insight(raw_text="One.", source="git/pr:9", scope="repo", category="convention"),
        Insight(raw_text="Two.", source="git/commit:abc", scope="file:y.py", category="rejected"),
    ]
    assert serialize_facts(insights) == serialize_facts(insights)
    assert serialize_insights(insights) == serialize_insights(insights)
    assert serialize_facts(insights) == "One.\nTwo.\n"
