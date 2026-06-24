"""Lift legacy ``candidates`` rows onto the unified ``facts`` spine (yoyo step).

Historically this ran as the first step of the hand-rolled
``m2026_06_23_unify_facts`` module. It is now a tracked yoyo migration so it
runs exactly once per database (recorded in ``_yoyo_migration``).

For every ``candidates`` row under ``(praxis, *)`` it inserts a ``facts`` row
under the real ``(praxis, USER)`` tenant (reusing the id), embedding
``doc.content`` and recreating contradiction links as ``fact_edges``.

Guarded + re-runnable: it no-ops when the ``candidates`` table is absent (e.g.
a fresh DB or a database where the table was already dropped), and inserts use
``ON CONFLICT DO NOTHING``.
"""

from __future__ import annotations

from yoyo import step

# Target tenant: the real praxis user.
ORG = "praxis"
USER = "24782438-1091-70d3-3e55-f9f3510b2aba"


def reembed_candidates(conn) -> None:
    """yoyo apply step. ``conn`` is the psycopg3 backend connection."""
    # yoyo execs this file without the repo root on sys.path; add it so the
    # `knowledge` package (embedder, vector helpers) imports cleanly.
    import sys
    from pathlib import Path

    repo_root = str(Path(__file__).resolve().parent.parent)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    from psycopg.types.json import Jsonb

    from knowledge.knowledge_graph.knowledge_graph_variants.postgres_vector_graph import (
        _fit,
    )
    from knowledge.llm.embedder_variants.openrouter_embedder import OpenRouterEmbedder

    # Round-trip embeddings as python lists. Best-effort: a DB without the
    # `vector` type (or no candidates to move) still completes fine.
    try:
        from pgvector.psycopg import register_vector

        register_vector(conn)
    except Exception:
        pass

    cur = conn.cursor()
    cur.execute("SELECT to_regclass('public.candidates') IS NOT NULL")
    row = cur.fetchone()
    if not (row and row[0]):
        print("reembed: no `candidates` table — migrated 0")
        return

    cur.execute("SELECT doc FROM candidates WHERE org_id = %s", (ORG,))
    rows = cur.fetchall()
    if not rows:
        print("reembed: no candidate rows — migrated 0")
        return

    embedder = OpenRouterEmbedder()
    migrated = 0
    docs: list[dict] = []
    for (doc,) in rows:
        if not isinstance(doc, dict):
            continue
        fact_id = doc.get("id")
        if not fact_id:
            continue
        docs.append(doc)

        content = str(doc.get("content") or "")
        meta = {
            "title": doc.get("title"),
            "auditTrail": doc.get("auditTrail") or doc.get("audit_trail") or [],
        }
        embedding = _fit(embedder.embed_one(content)) if content else None

        cur.execute(
            """
            INSERT INTO facts
                (id, org_id, user_id, text, source, confidence, state,
                 observation_count, embedding, meta)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 1, %s, %s)
            ON CONFLICT (org_id, user_id, id) DO NOTHING
            RETURNING id
            """,
            (
                fact_id,
                ORG,
                USER,
                content,
                doc.get("provenance"),
                doc.get("confidence"),
                doc.get("state") or "proposed",
                embedding,
                Jsonb(meta),
            ),
        )
        if cur.fetchone() is not None:
            migrated += 1

    # Recreate contradiction links now that all facts have been inserted.
    cur.execute(
        "SELECT id FROM facts WHERE org_id = %s AND user_id = %s", (ORG, USER)
    )
    existing = {r[0] for r in cur.fetchall()}
    edges = 0
    for doc in docs:
        fact_id = doc.get("id")
        rivals = doc.get("contradiction_ids") or doc.get("contradictions") or []
        for rival in rivals:
            if fact_id not in existing or rival not in existing:
                continue
            cur.execute(
                """
                INSERT INTO fact_edges (org_id, user_id, src_id, dst_id, kind)
                VALUES (%s, %s, %s, %s, 'contradiction')
                ON CONFLICT DO NOTHING
                RETURNING src_id
                """,
                (ORG, USER, fact_id, rival),
            )
            if cur.fetchone() is not None:
                edges += 1

    print(f"reembed: migrated {migrated} candidate(s) -> facts; created {edges} edge(s)")


steps = [step(reembed_candidates)]
