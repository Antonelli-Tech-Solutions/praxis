"""Per-viewer mounted-snapshot set: the read-only overlay selection.

A *mount* records that when ``(org_id, user_id)`` does a retrieval read, the
backend should also expose the facts of a saved snapshot
(``snapshot:<snapshot_name>``) owned by ``source_user_id`` — without merging
that snapshot into the viewer's live graph. Mounts are a read-time concern only
(see :mod:`knowledge.knowledge_graph.knowledge_graph_variants.overlay_graph`):
writes/ingest and saving a snapshot operate on the live ``facts`` table alone,
so a mounted overlay is never carried into a save.

``source_user_id`` may be the viewer themselves (mount your own snapshot) or any
other org member (read within the org trust boundary). Membership and snapshot
existence are validated by the route before calling :meth:`mount`; this store is
a thin, idempotent persistence layer over the ``mounted_snapshots`` table,
mirroring :class:`knowledge.serve.orgs_store.OrgsStore`.
"""

from __future__ import annotations

import psycopg


class MountedStore:
    """Mounted read-only snapshot overlays persisted to ``mounted_snapshots``."""

    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def list(self, org_id: str, user_id: str) -> list[dict]:
        """Return the viewer's mounts as ``{source_user_id, snapshot_name}`` rows."""
        rows = self._conn.execute(
            """
            SELECT source_user_id, snapshot_name
            FROM mounted_snapshots
            WHERE org_id = %s AND user_id = %s
            ORDER BY source_user_id, snapshot_name
            """,
            (org_id, user_id),
        ).fetchall()
        return [{"source_user_id": r[0], "snapshot_name": r[1]} for r in rows]

    def mount(
        self, org_id: str, user_id: str, source_user_id: str, snapshot_name: str
    ) -> None:
        """Add a mount (idempotent). Validation is the caller's responsibility."""
        self._conn.execute(
            """
            INSERT INTO mounted_snapshots (org_id, user_id, source_user_id, snapshot_name)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (org_id, user_id, source_user_id, snapshot_name) DO NOTHING
            """,
            (org_id, user_id, source_user_id, snapshot_name),
        )

    def unmount(
        self, org_id: str, user_id: str, source_user_id: str, snapshot_name: str
    ) -> None:
        """Remove a mount (no-op if it was not mounted)."""
        self._conn.execute(
            """
            DELETE FROM mounted_snapshots
            WHERE org_id = %s AND user_id = %s
              AND source_user_id = %s AND snapshot_name = %s
            """,
            (org_id, user_id, source_user_id, snapshot_name),
        )
