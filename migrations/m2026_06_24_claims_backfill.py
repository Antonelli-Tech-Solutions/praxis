"""One-off, idempotent backfill + re-evaluate migration for the structural
contradiction path (U7 of the structural-contradiction-detection plan).

Run once against the configured Postgres:

    python -m migrations.m2026_06_24_claims_backfill

It does two guarded, re-runnable things, over BOTH the live spine
(``facts``/``fact_edges``) and every cached state (``cached_facts``/
``cached_fact_edges`` per ``cache_key``):

1. **Backfill claims.** For every fact that has no claims yet, extract atomic
   (subject, attribute, value) claims with the structural extractor
   (``ClaimExtractionJudge``, replayed from a ``VerdictCassette`` so it is
   deterministic/cacheable) and persist them to ``claims``/``cached_claims``.
   Facts that already have claims are skipped (idempotent). Extraction only
   calls the live model when ``OPENROUTER_API_KEY`` is set; otherwise it is
   cassette-only (a cassette miss is a loud error, never a silent guess).

2. **Re-evaluate contradiction edges.** Recompute ``kind='contradiction'``
   edges purely from the new structural detector over the backfilled claims,
   then reconcile each tenant/cache_key's edge set to match: ADD newly-found
   real conflicts and DELETE edges the structural detector no longer supports
   (this clears the known cosine-era false positives). Re-evaluation only
   touches contradiction edges; it never changes fact ``state`` and never
   auto-resolves.

Before mutating edges it prints the current contradiction edge set per scope
(an ``Execution note``-style characterization) so the diff is auditable.

Idempotent: a second run extracts no new claims (all facts already have them)
and the recomputed edge set already equals the stored set, so it adds and
removes nothing.
"""

from __future__ import annotations

import os
from collections import defaultdict

from knowledge.knowledge_graph.knowledge_graph_def import Claim
from knowledge.knowledge_graph.write_policy.write_step_variants.claim_conflict_detector import (
    ClaimConflictDetector,
    ClaimValueJudge,
)
from knowledge.knowledge_graph.write_policy.write_step_variants.claim_extractor import (
    ClaimExtractionJudge,
)
from knowledge.serve.db import connect

# Model + cassette used for deterministic claim extraction and the gray-zone
# value judge. Mirrors the eval axis default (`conflict_model: openai/gpt-4o-mini`).
EXTRACT_MODEL = os.environ.get("PRAXIS_CLAIM_MODEL", "openai/gpt-4o-mini")


# --- pure helpers (no DB; unit-testable) -----------------------------------
def normalized_pair(a: str, b: str) -> tuple[str, str]:
    """A contradiction edge is undirected — canonicalize the pair (sorted)."""
    return (a, b) if a <= b else (b, a)


def compute_contradiction_edges(
    fact_claims: dict[str, list[Claim]],
    detector: ClaimConflictDetector,
) -> set[tuple[str, str]]:
    """Structural contradiction edges over a tenant's facts, as undirected pairs.

    ``fact_claims`` maps ``fact_id -> [Claim]``. For every functional slot
    asserted by more than one fact, compare the competing values with the same
    ``ClaimConflictDetector._incompatible`` logic the write path uses (numeric
    clash = deterministic conflict; fuzzy = gray-zone value judge; equal /
    uncertain = no edge). Pure: does no DB I/O, so the migration's core can be
    tested offline against a fixture.
    """
    # slot -> [(fact_id, raw_value)] for functional claims only.
    slot_values: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
    for fact_id, claims in fact_claims.items():
        seen_slots: set[tuple[str, str]] = set()
        for c in claims:
            if not c.functional:
                continue
            slot = c.slot
            # One value per (fact, slot): first functional claim wins, matching
            # the write path's "last wins" dict by being deterministic per fact.
            if slot in seen_slots:
                continue
            seen_slots.add(slot)
            slot_values[slot].append((fact_id, c.value))

    edges: set[tuple[str, str]] = set()
    for slot, members in slot_values.items():
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                fid_a, val_a = members[i]
                fid_b, val_b = members[j]
                if fid_a == fid_b:
                    continue
                if detector._incompatible(slot, val_a, val_b):
                    edges.add(normalized_pair(fid_a, fid_b))
    return edges


def edges_match(
    stored: set[tuple[str, str]], computed: set[tuple[str, str]]
) -> tuple[set[tuple[str, str]], set[tuple[str, str]]]:
    """Return (to_add, to_remove) reconciling the stored edge set to ``computed``.

    Both inputs are sets of normalized undirected pairs. Pure set diff — makes
    the idempotency contract (empty diff on a second run) trivially checkable.
    """
    return (computed - stored, stored - computed)


# --- DB plumbing ------------------------------------------------------------
def _build_judges() -> tuple[ClaimExtractionJudge, ClaimConflictDetector]:
    """Cassette-backed extractor + detector. Live model only when a key is set."""
    from pathlib import Path

    from knowledge.llm.verdict_cassette import VerdictCassette

    has_key = bool(os.environ.get("OPENROUTER_API_KEY"))
    llm = None
    if has_key:
        from knowledge.llm.llm_variants.openrouter_llm import OpenRouterLlm

        llm = OpenRouterLlm(model=EXTRACT_MODEL)

    # Reuse the committed eval cassettes so extraction/value verdicts replay the
    # same way evals do (paths mirror knowledge/evals/run.py).
    here = Path(__file__).resolve().parents[1]
    verdicts = here / "knowledge" / "evals" / "fixtures" / "verdicts"
    slug = EXTRACT_MODEL.replace("/", "_").replace(":", "_")
    extract_cache = verdicts / "claim_extract" / f"{slug}.json"
    value_cache = verdicts / "conflict" / f"{slug}.json"

    extract_cassette = (
        VerdictCassette(extract_cache, model_id=EXTRACT_MODEL, allow_compute=has_key)
        if (extract_cache.exists() or has_key)
        else None
    )
    value_cassette = (
        VerdictCassette(value_cache, model_id=EXTRACT_MODEL, allow_compute=has_key)
        if (value_cache.exists() or has_key)
        else None
    )
    extractor = ClaimExtractionJudge(llm=llm, cassette=extract_cassette)
    detector = ClaimConflictDetector(
        judge=ClaimValueJudge(llm=llm, cassette=value_cassette)
    )
    return extractor, detector


def _scopes(conn, facts_table: str) -> list[tuple]:
    """All (org_id, user_id[, cache_key]) scopes present in a facts table.

    Each is one tenant graph the backfill operates over independently.
    """
    if facts_table == "cached_facts":
        rows = conn.execute(
            "SELECT DISTINCT org_id, user_id, cache_key FROM cached_facts"
        ).fetchall()
        return [(r[0], r[1], r[2]) for r in rows]
    rows = conn.execute("SELECT DISTINCT org_id, user_id FROM facts").fetchall()
    return [(r[0], r[1], None) for r in rows]


def _scope_label(org: str, user: str, cache_key: str | None) -> str:
    base = f"({org}, {user})"
    return f"{base} [{cache_key}]" if cache_key else base


def _claims_for(conn, claims_table, org, user, fact_id, cache_key):
    sql = (
        f"SELECT subject, attribute, value, functional FROM {claims_table} "
        "WHERE org_id=%s AND user_id=%s AND fact_id=%s"
    )
    params: list[object] = [org, user, fact_id]
    if cache_key is not None:
        sql += " AND cache_key=%s"
        params.append(cache_key)
    sql += " ORDER BY seq"
    return [
        Claim(subject=r[0], attribute=r[1], value=r[2], functional=r[3])
        for r in conn.execute(sql, params).fetchall()
    ]


def _facts_with_claim_flag(conn, facts_table, claims_table, org, user, cache_key):
    """Yield (fact_id, text, has_any_claim) for one scope."""
    sql = (
        f"SELECT f.id, f.text, EXISTS (SELECT 1 FROM {claims_table} c "
        "WHERE c.org_id=f.org_id AND c.user_id=f.user_id AND c.fact_id=f.id"
    )
    params: list[object] = []
    if cache_key is not None:
        sql += " AND c.cache_key=%s"
        params.append(cache_key)
    sql += ") AS has_claims FROM " + facts_table + " f WHERE f.org_id=%s AND f.user_id=%s"
    params += [org, user]
    if cache_key is not None:
        sql += " AND f.cache_key=%s"
        params.append(cache_key)
    return conn.execute(sql, params).fetchall()


def _insert_claims(conn, claims_table, org, user, fact_id, cache_key, claims):
    for seq, c in enumerate(claims):
        cols = ["org_id", "user_id"]
        vals: list[object] = [org, user]
        if cache_key is not None:
            cols.append("cache_key")
            vals.append(cache_key)
        cols += ["fact_id", "seq", "subject", "attribute", "value", "functional"]
        vals += [fact_id, seq, Claim.norm(c.subject), Claim.norm(c.attribute),
                 c.value, c.functional]
        placeholders = ", ".join(["%s"] * len(vals))
        conn.execute(
            f"INSERT INTO {claims_table} ({', '.join(cols)}) "
            f"VALUES ({placeholders}) ON CONFLICT DO NOTHING",
            vals,
        )


def _stored_edges(conn, edges_table, org, user, cache_key) -> set[tuple[str, str]]:
    sql = (
        f"SELECT src_id, dst_id FROM {edges_table} "
        "WHERE org_id=%s AND user_id=%s AND kind='contradiction'"
    )
    params: list[object] = [org, user]
    if cache_key is not None:
        sql += " AND cache_key=%s"
        params.append(cache_key)
    return {
        normalized_pair(r[0], r[1])
        for r in conn.execute(sql, params).fetchall()
    }


def _add_edge(conn, edges_table, org, user, cache_key, src, dst):
    cols = ["org_id", "user_id"]
    vals: list[object] = [org, user]
    if cache_key is not None:
        cols.append("cache_key")
        vals.append(cache_key)
    cols += ["src_id", "dst_id", "kind"]
    vals += [src, dst, "contradiction"]
    placeholders = ", ".join(["%s"] * len(vals))
    conn.execute(
        f"INSERT INTO {edges_table} ({', '.join(cols)}) "
        f"VALUES ({placeholders}) ON CONFLICT DO NOTHING",
        vals,
    )


def _remove_edge(conn, edges_table, org, user, cache_key, a, b):
    # Contradictions are undirected — delete either stored orientation.
    sql = (
        f"DELETE FROM {edges_table} WHERE org_id=%s AND user_id=%s "
        "AND kind='contradiction' "
        "AND ((src_id=%s AND dst_id=%s) OR (src_id=%s AND dst_id=%s))"
    )
    params: list[object] = [org, user, a, b, b, a]
    if cache_key is not None:
        sql += " AND cache_key=%s"
        params.append(cache_key)
    conn.execute(sql, params)


def _backfill_scope(
    conn, facts_table, claims_table, edges_table, org, user, cache_key,
    extractor, detector,
) -> dict:
    """Backfill claims + re-evaluate edges for one tenant/cache_key scope."""
    label = _scope_label(org, user, cache_key)

    # --- step A: backfill claims for facts that have none yet ---------------
    claims_added = 0
    facts_processed = 0
    for fact_id, text, has_claims in _facts_with_claim_flag(
        conn, facts_table, claims_table, org, user, cache_key
    ):
        facts_processed += 1
        if has_claims:
            continue  # idempotent: never re-extract a fact that already has claims
        extracted = extractor.extract(text or "")
        if not extracted:
            continue  # no source / no checkable claim -> skip without error
        _insert_claims(conn, claims_table, org, user, fact_id, cache_key, extracted)
        claims_added += len(extracted)

    # --- step B: recompute the contradiction edge set -----------------------
    fact_ids = [
        r[0]
        for r in _facts_with_claim_flag(
            conn, facts_table, claims_table, org, user, cache_key
        )
    ]
    fact_claims = {
        fid: _claims_for(conn, claims_table, org, user, fid, cache_key)
        for fid in fact_ids
    }
    computed = compute_contradiction_edges(fact_claims, detector)
    stored = _stored_edges(conn, edges_table, org, user, cache_key)

    # Execution-note characterization: print the BEFORE edge set so the
    # mutation diff is auditable.
    print(f"  {label}: current contradiction edges = {sorted(stored)}")

    to_add, to_remove = edges_match(stored, computed)
    for a, b in sorted(to_add):
        _add_edge(conn, edges_table, org, user, cache_key, a, b)
    for a, b in sorted(to_remove):
        _remove_edge(conn, edges_table, org, user, cache_key, a, b)

    print(
        f"  {label}: facts={facts_processed} claims_added={claims_added} "
        f"edges_added={len(to_add)} edges_removed={len(to_remove)}"
    )
    return {
        "claims_added": claims_added,
        "edges_added": len(to_add),
        "edges_removed": len(to_remove),
    }


def _backfill_table(conn, facts_table, extractor, detector) -> dict:
    """Run the backfill over every scope of one facts table (live or cache)."""
    claims_table = "cached_claims" if facts_table == "cached_facts" else "claims"
    edges_table = "cached_fact_edges" if facts_table == "cached_facts" else "fact_edges"
    totals = {"claims_added": 0, "edges_added": 0, "edges_removed": 0}
    scopes = _scopes(conn, facts_table)
    print(f"{facts_table}: {len(scopes)} scope(s)")
    for org, user, cache_key in scopes:
        res = _backfill_scope(
            conn, facts_table, claims_table, edges_table,
            org, user, cache_key, extractor, detector,
        )
        for k in totals:
            totals[k] += res[k]
    print(
        f"{facts_table} TOTAL: claims_added={totals['claims_added']} "
        f"edges_added={totals['edges_added']} edges_removed={totals['edges_removed']}"
    )
    return totals


def main() -> None:
    from dotenv import load_dotenv

    load_dotenv()

    extractor, detector = _build_judges()
    with connect() as conn:  # registers the pgvector adapter
        _backfill_table(conn, "facts", extractor, detector)
        _backfill_table(conn, "cached_facts", extractor, detector)
    print("migration complete.")


if __name__ == "__main__":
    main()
