"""Bridge the knowledge store's contradiction signal into the candidate-api shape.

``serialize_pairs`` turns the candidates' contradiction links into the wire
shape the dashboard's GET /contradictions endpoint returns (one entry per unique
pair). ``detect`` is the live path: it runs the candidate texts through a real
``VectorGraph`` (whose write-policy includes the LLM ConflictFlagger) and returns
candidate-id pairs it flags — best-effort, so offline / no-API-key yields [].
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Callable

from knowledge.knowledge_graph.knowledge_graph_variants.vector_graph import VectorGraph

Candidate = dict[str, Any]

# A slot is the normalized (subject, attribute) key a functional claim occupies.
Slot = tuple[str, str]
# Maps a fact id to (slot, value) for the functional claim it holds, if any.
SlotInfo = dict[str, tuple[Slot, str]]


def _cid(c: Candidate) -> str:
    return str(c.get("id", ""))


def contradiction_ids(c: Candidate) -> list[str]:
    raw = c.get("contradiction_ids") or c.get("contradictions") or []
    return [str(x.get("id") if isinstance(x, dict) else x) for x in raw]


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


def _member(c: Candidate, slot_info: SlotInfo) -> dict[str, Any]:
    """A summary plus the fact's value on the cluster's slot (if known)."""
    m = _summary(c)
    info = slot_info.get(_cid(c))
    m["value"] = info[1] if info else ""
    return m


def serialize_clusters(
    candidates: list[Candidate],
    slot_info: SlotInfo | None = None,
) -> list[dict[str, Any]]:
    """Group contradiction pairs into one cluster per conflicting claim slot.

    A cluster collects all facts that compete on the same normalized
    (subject, attribute) slot, listing each member's value on that slot. Two
    facts join the same cluster when they are linked by a contradiction pair OR
    when they share a non-empty slot. A plain 2-fact conflict is a cluster of
    size 2 (no regression). Each cluster carries the underlying pairwise
    ``pairs`` so the existing per-pair resolve flow keeps working unchanged.

    ``slot_info`` maps a fact id to its functional claim's (slot, value); pass it
    from the claims table (or in-memory ``Fact.claims``). When empty, every pair
    degrades to its own cluster of two.
    """
    slot_info = slot_info or {}
    pairs = serialize_pairs(candidates)
    by_id = {_cid(c): c for c in candidates}

    # Union-find over fact ids: merge pair endpoints and same-slot facts.
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    members_in_pairs: set[str] = set()
    for p in pairs:
        a, b = p["a"]["id"], p["b"]["id"]
        members_in_pairs.update((a, b))
        union(a, b)
    # Merge facts that share a slot even if only chained pairwise.
    by_slot: dict[Slot, list[str]] = {}
    for fid in members_in_pairs:
        info = slot_info.get(fid)
        if info:
            by_slot.setdefault(info[0], []).append(fid)
    for fids in by_slot.values():
        for other in fids[1:]:
            union(fids[0], other)

    groups: dict[str, list[str]] = {}
    for fid in members_in_pairs:
        groups.setdefault(find(fid), []).append(fid)
    pairs_by_root: dict[str, list[dict[str, Any]]] = {}
    for p in pairs:
        pairs_by_root.setdefault(find(p["a"]["id"]), []).append(p)

    out: list[dict[str, Any]] = []
    for root, member_ids in groups.items():
        member_ids = sorted(member_ids)
        cluster_pairs = pairs_by_root.get(root, [])
        # Pick the slot most members agree on (None when no claims are stored).
        slot_votes = Counter(
            slot_info[mid][0] for mid in member_ids if mid in slot_info
        )
        slot = slot_votes.most_common(1)[0][0] if slot_votes else None
        members = [_member(by_id[mid], slot_info) for mid in member_ids if mid in by_id]
        out.append(
            {
                "id": "__".join(member_ids),
                "slot": {"subject": slot[0], "attribute": slot[1]} if slot else None,
                "status": "pending",
                "members": members,
                "pairs": cluster_pairs,
            }
        )
    out.sort(key=lambda c: c["id"])
    return out


def detect(candidates: list[Candidate]) -> list[tuple[str, str]]:
    """Run candidate texts through a real VectorGraph; return flagged id pairs.

    Best-effort: the LLM contradiction check is skipped when no API key is set,
    so this returns [] offline. Maps the flagged facts back to candidate ids by
    matching the stored text.

    With a key, embed with the real OpenRouter embedder so semantically-related
    candidates actually clear the recall floor and reach the ConflictJudge — the
    default ``FakeEmbedder`` produces near-zero similarity between distinct texts,
    so the judge would never be consulted and nothing would ever flag.
    """
    import os

    embedder = None
    if os.getenv("OPENROUTER_API_KEY"):
        from knowledge.llm.embedder_variants.openrouter_embedder import OpenRouterEmbedder

        embedder = OpenRouterEmbedder()
    graph = VectorGraph(embedder=embedder)
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
