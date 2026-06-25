"""Deterministic checks over the seeded knowledge graph (ingestion guardrails).

Unlike the :mod:`text` / :mod:`builds` checks (which inspect the agent's output
artifact), these assert that the *seed* actually populated the graph. The only
graph-derived signal a check can see is :attr:`EvalContext.injected_knowledge` —
the reader's output, i.e. the ``active`` fact texts the agent was shown (joined
by blank lines by the whole-file reader / graph ``read``). That makes it a faithful
proxy for "what landed active and retrievable": a no-op ingestor (zero active
image cards, zero active Wikipedia facts) shows up here as missing blocks, so
these checks FAIL the eval instead of letting the gap pass silently.

Each takes the :class:`EvalContext` plus the case's ``params`` and returns a
:class:`CheckResult`.
"""

from __future__ import annotations

import uuid

from knowledge.evals.eval_def import CheckResult, EvalContext

# Image/asset cards from the ImageIngestor carry the ``assets/<file>`` reference
# in their card text (see image_injestor.py: "path=assets/" convention).
_ASSET_MARKER = "path=assets/"


def _active_blocks(ctx: EvalContext) -> list[str]:
    """The active fact blocks the reader injected, split on the blank-line join.

    The whole-file reader concatenates active fact texts with ``\\n\\n`` (graph
    ``read``); split on that and drop empties.
    """
    raw = ctx.injected_knowledge or ""
    return [b.strip() for b in raw.split("\n\n") if b.strip()]


def min_active_asset_cards(ctx: EvalContext, *, minimum: int = 1) -> CheckResult:
    """Pass iff at least ``minimum`` active image/asset cards were seeded.

    Counts injected fact blocks bearing the ImageIngestor's ``path=assets/``
    marker. Guards against the image ingestor producing ZERO active asset cards
    (a silent no-op the rubric/text checks can't catch).
    """
    cards = [b for b in _active_blocks(ctx) if _ASSET_MARKER in b]
    ok = len(cards) >= minimum
    return CheckResult(
        name="min_active_asset_cards",
        passed=ok,
        evidence=(
            f"{len(cards)} active asset card(s) (need >= {minimum})"
            if ok
            else f"only {len(cards)} active asset card(s) injected (need >= {minimum}); "
            "image ingestion produced no retrievable asset cards"
        ),
    )


def at_most_one_active(
    ctx: EvalContext, *, texts: list[str], winner: str | None = None
) -> CheckResult:
    """FR-005 guard: of a mutually-contradictory ``texts`` pair, never more than one
    is active.

    Active facts are read from ``injected_knowledge`` (the reader's output). The
    offline ``FakeRunner`` injects nothing, so with no injected knowledge the check
    is not applicable and passes -- it bites only on a real run that shows the agent
    the seeded graph, where the write policy's FR-005 enforcement should have
    demoted the losing side to ``proposed`` (hence out of the active read). With
    ``winner`` set, a single active side must be that text (the seed that wins the
    tie / stays live).
    """
    blocks = _active_blocks(ctx)
    if not blocks:
        return CheckResult(
            name="at_most_one_active",
            passed=True,
            evidence="no injected knowledge (live-run check; not applicable offline)",
        )
    live = [t for t in texts if any(t.strip() in b for b in blocks)]
    if len(live) > 1:
        return CheckResult(
            name="at_most_one_active",
            passed=False,
            evidence=f"FR-005 violated: {len(live)} contradictory facts are both active: {live!r}",
        )
    if winner is not None and live and live != [winner]:
        return CheckResult(
            name="at_most_one_active",
            passed=False,
            evidence=f"the live side is {live!r}, expected the winner {winner!r}",
        )
    return CheckResult(
        name="at_most_one_active",
        passed=True,
        evidence=f"<= 1 of the contradictory pair is active: {live!r}",
    )


def retrieves_fact_for_query(
    ctx: EvalContext,
    *,
    seed_facts: list[str],
    query: str,
    expect_substring: str,
    top_k: int = 3,
) -> CheckResult:
    """Pass iff ``search(query, top_k)`` over ``seed_facts`` surfaces ``expect_substring``.

    This is the hybrid-retrieval (vector + BM25 via RRF) regression check. It
    drives the *real* user-facing retrieval path on the Postgres store: it seeds
    ``seed_facts`` as active facts into a fresh, isolated ``(org_id, user_id)``
    tenant, runs ``search`` with the cached (offline, deterministic) embedder, and
    asserts the fact containing ``expect_substring`` lands in the top-``top_k`` hits.

    The case is built so the keyword fact ranks OUT of top-k under pure pgvector
    cosine (RED on the unmodified store) and IN once a BM25 keyword branch is fused
    in with Reciprocal Rank Fusion (GREEN). Deterministic and offline: the cached
    embedder replays committed real vectors (recording misses only with a key), and
    Postgres full-text ranking is fully deterministic.

    Requires a reachable Postgres DSN (the case declares ``embedder: cached`` /
    ``substrate: vector``); without one the harness SKIPs the case before it runs.
    """
    from knowledge.evals.run import _eval_embedder
    from knowledge.knowledge_graph.knowledge_graph_variants.postgres_vector_graph import (
        PostgresVectorGraph,
    )
    from knowledge.knowledge_graph.write_policy.write_step_variants import Deduper, Redactor
    from knowledge.serve import db

    # Resolve the same cached embedder the harness wires for an ``embedder: cached``
    # case (committed real vectors, deterministic offline).
    class _CachedAxis:
        embedder = "cached"

    embedder = _eval_embedder(_CachedAxis())

    conn = db.connect()
    db.bootstrap()  # ensure the tsvector column / GIN index exist on this DB
    org = "eval_hybrid_" + uuid.uuid4().hex[:12]
    user = "u1"
    graph = PostgresVectorGraph(
        conn,
        org,
        user,
        embedder=embedder,
        # Distinct seed texts must coexist (no overwrite/merge collapse): a plain
        # redact + exact-dedup policy keeps each fact as its own active row.
        policy=[Redactor(), Deduper()],
    )
    try:
        for text in seed_facts:
            graph.write(text, state="active")
        hits = graph.search(query, top_k=top_k)
        texts = [h.fact.text for h in hits]
        found = any(expect_substring in t for t in texts)
        return CheckResult(
            name="retrieves_fact_for_query",
            passed=found,
            evidence=(
                f"top-{top_k} for {query!r} includes a fact with {expect_substring!r}: {texts!r}"
                if found
                else f"top-{top_k} for {query!r} MISSED {expect_substring!r}; got {texts!r}"
            ),
        )
    finally:
        # Drop the throwaway tenant so the live store isn't polluted across runs.
        conn.execute("DELETE FROM facts WHERE org_id = %s AND user_id = %s", (org, user))


def min_non_seed_facts(
    ctx: EvalContext, *, minimum: int = 1, seed_texts: list[str] | None = None
) -> CheckResult:
    """Pass iff at least ``minimum`` active facts are neither seed nor asset cards.

    ``seed_texts`` is the case's hand-authored ``direct_to_graph`` facts (passed
    verbatim by the case). An injected active block that is not one of those and
    not an asset card must have come from the ``via_ingestor`` text (the Wikipedia
    article) — i.e. a retrievable, non-seed text fact. Guards against the text
    ingestor contributing ZERO retrievable Wikipedia-derived facts.
    """
    seeds = {s.strip() for s in (seed_texts or [])}
    derived = [
        b
        for b in _active_blocks(ctx)
        if _ASSET_MARKER not in b and b not in seeds
    ]
    ok = len(derived) >= minimum
    return CheckResult(
        name="min_non_seed_facts",
        passed=ok,
        evidence=(
            f"{len(derived)} active non-seed text fact(s) (need >= {minimum})"
            if ok
            else f"only {len(derived)} active non-seed text fact(s) injected (need >= {minimum}); "
            "text ingestion contributed no retrievable Wikipedia-derived facts"
        ),
    )
