"""Bridge the knowledge store's contradiction signal into the candidate-api shape.

``serialize_pairs`` turns the candidates' contradiction links into the wire
shape the dashboard's GET /contradictions endpoint returns (one entry per unique
pair). ``detect`` is the live path: it runs the candidate texts through a real
``VectorGraph`` (whose write-policy includes the LLM ConflictFlagger) and returns
candidate-id pairs it flags — best-effort, so offline / no-API-key yields [].
"""

from __future__ import annotations

from typing import Any

from knowledge.knowledge_graph.knowledge_graph_variants.vector_graph import VectorGraph
from knowledge.serve.store import Candidate, _cid, contradiction_ids


def _summary(c: Candidate) -> dict[str, Any]:
    return {
        "id": _cid(c),
        "title": str(c.get("title", "")),
        "content": str(c.get("content", "")),
        "provenance": str(c.get("provenance", c.get("source", ""))),
        "state": str(c.get("state", "proposed")),
    }


def serialize_pairs(candidates: list[Candidate]) -> list[dict[str, Any]]:
    """Unique contradiction pairs in the candidate-api shape (best id first)."""
    by_id = {_cid(c): c for c in candidates}
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for c in candidates:
        for rival_id in contradiction_ids(c):
            rival = by_id.get(rival_id)
            if rival is None:
                continue
            a, b = sorted((_cid(c), rival_id))
            if a in (None, "") or f"{a}__{b}" in seen:
                continue
            seen.add(f"{a}__{b}")
            out.append({"id": f"{a}__{b}", "status": "pending", "a": _summary(by_id[a]), "b": _summary(by_id[b])})
    return out


def detect(candidates: list[Candidate]) -> list[tuple[str, str]]:
    """Run candidate texts through a real VectorGraph; return flagged id pairs.

    Best-effort: the LLM contradiction check is skipped when no API key is set,
    so this returns [] offline. Maps the flagged facts back to candidate ids by
    matching the stored text.
    """
    graph = VectorGraph()
    text_to_id: dict[str, str] = {}
    for c in candidates:
        content = str(c.get("content", "")).strip()
        if content:
            text_to_id[content] = _cid(c)
            graph.write(content)
    pairs: list[tuple[str, str]] = []
    for con in graph.contradictions():
        a = text_to_id.get(con.flagged.text.strip())
        b = text_to_id.get(con.conflicting.text.strip())
        if a and b and a != b:
            pairs.append((a, b))
    return pairs
