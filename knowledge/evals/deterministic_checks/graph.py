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


def single_merged_fact(
    ctx: EvalContext, *, mentions: list[str], max_blocks: int = 1
) -> CheckResult:
    """Mem0 UPDATE/merge guard: the graph ends as ONE fact mentioning every term.

    For the knowledge_graph component, ``ctx.output`` is every stored fact text
    joined by blank lines (plus any ``CONTRADICTION:`` summary lines). Two related-
    additive notes should collapse to a SINGLE merged fact whose text contains all
    of ``mentions`` (e.g. both "cheese" and "chicken") — not two separate facts and
    not a flagged contradiction. Passes iff: at most ``max_blocks`` non-contradiction
    fact blocks exist, no ``CONTRADICTION:`` line is present, and exactly one block
    mentions all the required terms.
    """
    blocks = [b.strip() for b in ctx.output.split("\n\n") if b.strip()]
    fact_blocks = [b for b in blocks if not b.startswith("CONTRADICTION:")]
    has_contradiction = any("CONTRADICTION:" in b for b in blocks)
    merged = [b for b in fact_blocks if all(m.lower() in b.lower() for m in mentions)]
    ok = (
        not has_contradiction
        and len(fact_blocks) <= max_blocks
        and len(merged) == 1
    )
    if ok:
        evidence = f"single merged fact mentions {mentions!r}: {merged[0]!r}"
    elif has_contradiction:
        evidence = "a CONTRADICTION was flagged (expected an additive merge, not a clash)"
    elif len(fact_blocks) > max_blocks:
        evidence = (
            f"{len(fact_blocks)} fact blocks remain (expected <= {max_blocks}); "
            f"the additive notes were not merged: {fact_blocks!r}"
        )
    else:
        evidence = f"no single fact mentions all of {mentions!r}; blocks={fact_blocks!r}"
    return CheckResult(name="single_merged_fact", passed=ok, evidence=evidence)


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
        # Hybrid is opt-in (default off): this check exercises the keyword-fusion
        # path explicitly, since that is the capability under test.
        hits = graph.search(query, top_k=top_k, hybrid=True)
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


def retrieval_prefers_proven_over_failed(
    ctx: EvalContext,
    *,
    query: str,
    proven_text: str,
    failed_text: str,
    proven_confidence: float = 1.0,
    failed_confidence: float = 0.1,
    top_k: int = 2,
) -> CheckResult:
    """Outcome/trust-feedback red spec: a fact whose advice demonstrably FAILED
    must not outrank a PROVEN fact for the same query.

    Seeds two competing, both-``active`` facts answering the same question into a
    fresh isolated tenant:

      * ``failed_text`` — an approach that was tried and repeatedly failed. It is
        written to be *more lexically/semantically similar to the query* (it echoes
        the query's wording), so pure-similarity retrieval ranks it first.
      * ``proven_text`` — the approach that actually worked, phrased differently.

    The outcome history is expressed the only way Praxis lets us today: the failed
    fact is set to low ``confidence`` and the proven fact to high ``confidence``.
    The check then runs the real ``search`` and asserts the proven fact ranks ABOVE
    the failed one.

    This FAILS on the current store: ``search`` ranks purely by cosine (+ optional
    BM25) and **never consults ``confidence`` / any outcome signal** — so the failed
    approach, being more query-similar, wins. It demonstrates that outcome/trust-aware
    ranking is missing: there is no channel (existing ``confidence`` included) by which
    a demonstrably-bad fact loses to a proven one. It would PASS once retrieval is
    outcome/trust-weighted.

    Requires a reachable Postgres DSN (``embedder: cached`` / ``substrate: vector``);
    without one the harness SKIPs the case.
    """
    from knowledge.evals.run import _eval_embedder
    from knowledge.knowledge_graph.knowledge_graph_variants.postgres_vector_graph import (
        PostgresVectorGraph,
    )
    from knowledge.knowledge_graph.write_policy.write_step_variants import Deduper, Redactor
    from knowledge.serve import db

    class _CachedAxis:
        embedder = "cached"

    embedder = _eval_embedder(_CachedAxis())

    conn = db.connect()
    db.bootstrap()
    org = "eval_outcome_" + uuid.uuid4().hex[:12]
    user = "u1"
    graph = PostgresVectorGraph(
        conn, org, user, embedder=embedder, policy=[Redactor(), Deduper()]
    )
    try:
        graph.write(proven_text, state="active")
        graph.write(failed_text, state="active")
        # Express the outcome history with the only trust-like field that exists.
        for text, conf in ((proven_text, proven_confidence), (failed_text, failed_confidence)):
            conn.execute(
                "UPDATE facts SET confidence = %s WHERE org_id = %s AND user_id = %s AND text = %s",
                (conf, org, user, text),
            )
        hits = graph.search(query, top_k=top_k)
        ranked = [h.fact.text for h in hits]
        proven_rank = ranked.index(proven_text) if proven_text in ranked else 1_000
        failed_rank = ranked.index(failed_text) if failed_text in ranked else 1_000
        ok = proven_rank < failed_rank
        return CheckResult(
            name="retrieval_prefers_proven_over_failed",
            passed=ok,
            evidence=(
                f"proven fact (conf {proven_confidence}) ranks #{proven_rank} vs "
                f"failed fact (conf {failed_confidence}) #{failed_rank} for {query!r}"
                + (
                    ""
                    if ok
                    else " — retrieval ignored outcome/confidence and surfaced the "
                    "demonstrably-failed advice first (no outcome/trust signal in ranking)"
                )
            ),
        )
    finally:
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
