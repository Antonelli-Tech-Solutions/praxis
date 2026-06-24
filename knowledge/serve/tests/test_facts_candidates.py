"""Unit tests for the FactsCandidates facade over the facts spine.

These build the facade directly with a deterministic FakeEmbedder and a no-LLM
write policy ([Redactor(), Deduper()]), so they need a Postgres DSN but make no
network/LLM calls. Each test uses a unique throwaway org so runs never collide.
"""

from __future__ import annotations

import pytest

from knowledge.knowledge_graph.write_policy.write_step_variants import Deduper, Redactor
from knowledge.llm.embedder_variants.fake_embedder import FakeEmbedder
from knowledge.serve import db
from knowledge.serve.facts_candidates import FactsCandidates, PromotionError

pytestmark = pytest.mark.skipif(
    db.resolve_dsn() is None,
    reason="no Postgres DSN available (set PRAXIS_DB_URL or configure AWS secret)",
)

USER = "dev-user"


def _edge_pairs(facade, kind):
    """Undirected ``{frozenset(src, dst)}`` set of ``kind`` edges for the graph."""
    return {frozenset((s, d)) for s, d, _k in facade.graph.all_edges(kind)}


def _contra_status(candidate):
    """``{rival_id: status}`` from a candidate's rich ``contradictions`` field."""
    return {c["id"]: c["status"] for c in candidate.get("contradictions", [])}


def _pair(a, b):
    return f"{min(a, b)}__{max(a, b)}"


@pytest.fixture
def facade(unique_org):
    """A FactsCandidates bound to a fresh throwaway tenant (no LLM, fake embed)."""
    db.bootstrap()
    conn = db.connect()
    org = unique_org
    # Clean any prior run so the tenant starts empty and reruns stay isolated.
    conn.execute("DELETE FROM fact_edges WHERE org_id = %s", (org,))
    conn.execute("DELETE FROM facts WHERE org_id = %s", (org,))
    f = FactsCandidates(
        conn, org, USER, embedder=FakeEmbedder(), policy=[Redactor(), Deduper()]
    )
    yield f
    conn.execute("DELETE FROM fact_edges WHERE org_id = %s", (org,))
    conn.execute("DELETE FROM facts WHERE org_id = %s", (org,))
    conn.close()


def test_create_get_list_round_trip(facade):
    created = facade.create({"title": "Use uv", "content": "Use uv, not pip, in this repo."})
    cid = created["id"]
    assert created["state"] == "proposed"
    assert created["title"] == "Use uv"

    got = facade.get(cid)
    assert got is not None and got["id"] == cid
    assert got["content"] == "Use uv, not pip, in this repo."

    assert any(c["id"] == cid for c in facade.list())
    # State filter: proposed includes it, active does not.
    assert any(c["id"] == cid for c in facade.list("proposed"))
    assert not any(c["id"] == cid for c in facade.list("active"))


def test_get_unknown_returns_none(facade):
    assert facade.get("does-not-exist") is None


def test_promote_advances_proposed_to_active(facade):
    cid = facade.create({"title": "T", "content": "Prefer pytest over unittest."})["id"]
    promoted = facade.promote(cid)
    assert promoted["state"] == "active"
    assert facade.get(cid)["state"] == "active"


def test_promote_from_terminal_state_raises(facade):
    cid = facade.create({"title": "T", "content": "Deploy via CDK."})["id"]
    facade.promote(cid)  # proposed -> active (terminal)
    with pytest.raises(PromotionError):
        facade.promote(cid)


def test_promote_unknown_raises_keyerror(facade):
    with pytest.raises(KeyError):
        facade.promote("nope")


def test_reject_rejects(facade):
    cid = facade.create({"title": "T", "content": "Some noisy candidate text."})["id"]
    rejected = facade.reject(cid, reason="noise")
    assert rejected["state"] == "rejected"
    assert facade.get(cid)["state"] == "rejected"


def test_update_changes_title_and_content(facade):
    cid = facade.create({"title": "Old", "content": "Original content."})["id"]
    updated = facade.update(cid, {"title": "New", "content": "Edited content."})
    assert updated["title"] == "New"
    assert updated["content"] == "Edited content."
    assert facade.get(cid)["content"] == "Edited content."


def test_delete_then_get_and_keyerror(facade):
    cid = facade.create({"title": "T", "content": "Disposable candidate."})["id"]
    facade.delete(cid)
    assert facade.get(cid) is None
    with pytest.raises(KeyError):
        facade.delete(cid)


def test_contradiction_edge_surfaces_pair_and_resolves(facade):
    a = facade.create({"title": "A", "content": "Use tabs for indentation."})["id"]
    b = facade.create({"title": "B", "content": "Use spaces for indentation."})["id"]
    # Persist a contradiction edge directly on the spine (the policy here is
    # no-LLM, so we wire the edge ourselves to exercise the pair path).
    facade.graph.add_edge(a, b, "contradiction")

    pairs = facade.contradictions()
    assert len(pairs) == 1
    pair = pairs[0]
    assert pair["id"] == f"{min(a, b)}__{max(a, b)}"
    assert {pair["a"]["id"], pair["b"]["id"]} == {a, b}

    kept = facade.resolve(pair["id"], a)
    assert kept["id"] == a
    assert kept["state"] == "active"
    loser = facade.get(b)
    assert loser["state"] == "rejected"
    assert loser["content"] == "Use spaces for indentation."  # text intact (FR-004/SC-001)
    # Resolved, not deleted: the pending list drops it, but the link survives
    # flipped to contradicted_by so the resolution stays reversible (FR-004).
    assert facade.contradictions() == []
    assert _edge_pairs(facade, "contradicted_by") == {frozenset((a, b))}
    assert _edge_pairs(facade, "contradiction") == set()


def test_resolve_custom_rejects_both_and_creates_active(facade):
    a = facade.create({"title": "A", "content": "Store timestamps in UTC."})["id"]
    b = facade.create({"title": "B", "content": "Store timestamps in local time."})["id"]
    facade.graph.add_edge(a, b, "contradiction")
    pair_id = f"{min(a, b)}__{max(a, b)}"

    new = facade.resolve_custom(pair_id, "Store timestamps in UTC, render in local time.")
    assert new["state"] == "active"
    assert new["id"] not in (a, b)
    assert new["content"] == "Store timestamps in UTC, render in local time."
    assert facade.get(a)["state"] == "rejected"
    assert facade.get(b)["state"] == "rejected"
    assert facade.get(a)["content"] == "Store timestamps in UTC."  # text intact
    assert facade.get(b)["content"] == "Store timestamps in local time."  # text intact
    assert facade.contradictions() == []
    # Resolved by a third fact: the new fact links to each loser as
    # contradicted_by (auditable, FR-004); the old pending pair is gone.
    assert _edge_pairs(facade, "contradicted_by") == {
        frozenset((new["id"], a)),
        frozenset((new["id"], b)),
    }
    assert _edge_pairs(facade, "contradiction") == set()


# --- US2: review by state + contradictions ---------------------------------


def test_per_fact_contradictions_carry_status(facade):
    """FR-012: a fact's contradictions list both pending and resolved rivals, each
    annotated with its status."""
    a = facade.create({"title": "A", "content": "Use tabs."})["id"]
    b = facade.create({"title": "B", "content": "Use spaces."})["id"]
    c = facade.create({"title": "C", "content": "Use two spaces."})["id"]
    facade.graph.add_edge(a, b, "contradiction")  # stays pending
    facade.graph.add_edge(a, c, "contradiction")
    facade.resolve(_pair(a, c), a)  # a wins over c -> a<->c becomes resolved

    assert _contra_status(facade.get(a)) == {b: "pending", c: "resolved"}


def test_global_contradictions_lists_pending_only(facade):
    """FR-013a: the global view lists only pending pairs; resolved ones drop out."""
    a = facade.create({"title": "A", "content": "Use tabs."})["id"]
    b = facade.create({"title": "B", "content": "Use spaces."})["id"]
    c = facade.create({"title": "C", "content": "Use two spaces."})["id"]
    facade.graph.add_edge(a, b, "contradiction")  # pending
    facade.graph.add_edge(a, c, "contradiction")
    facade.resolve(_pair(a, c), a)  # resolved -> excluded from the pending view

    pairs = facade.contradictions()
    assert len(pairs) == 1
    assert pairs[0]["id"] == _pair(a, b)
    assert pairs[0]["status"] == "pending"


def test_reapprove_rejected_swaps_states_and_keeps_link(facade):
    """FR-010: re-approving a rejected fact flips it to active and demotes its
    active contradictor, keeping the link. FR-009: a fact linked only via a
    separate contradiction is not touched (no auto-cascade)."""
    a = facade.create({"title": "A", "content": "Use tabs."})["id"]
    b = facade.create({"title": "B", "content": "Use spaces."})["id"]
    facade.graph.add_edge(a, b, "contradiction")
    facade.resolve(_pair(a, b), a)  # a active, b rejected, linked contradicted_by
    assert facade.get(a)["state"] == "active"
    assert facade.get(b)["state"] == "rejected"

    # A separate fact d also contradicts a (pending) — must survive re-approval.
    d = facade.create({"title": "D", "content": "Use four spaces."})["id"]
    facade.graph.add_edge(a, d, "contradiction")

    result = facade.promote(b)  # re-approve the rejected fact
    assert result["state"] == "active"
    assert facade.get(b)["state"] == "active"
    assert facade.get(a)["state"] == "rejected"  # direct contradictor demoted
    assert facade.get(d)["state"] == "proposed"   # FR-009: untouched (created state)
    # The b<->a pair stays linked (resolved).
    assert frozenset((a, b)) in _edge_pairs(facade, "contradicted_by")
    # The action reports the demoted fact, with its other-contradictions flag.
    demoted = {r["id"]: r["hasOtherContradictions"] for r in result.get("rejected", [])}
    assert demoted.get(a) is True  # a also contradicts d


def test_reject_reports_other_contradictions(facade):
    """FR-008: a manual reject reports whether the fact has any contradiction."""
    a = facade.create({"title": "A", "content": "Alpha note."})["id"]
    b = facade.create({"title": "B", "content": "Beta note."})["id"]
    facade.graph.add_edge(a, b, "contradiction")
    assert facade.reject(a, reason="noise")["hasOtherContradictions"] is True

    lone = facade.create({"title": "L", "content": "Lonely note."})["id"]
    assert facade.reject(lone)["hasOtherContradictions"] is False


def test_resolve_loser_other_contradictions_flag(facade):
    """FR-008/SC-007: the resolve response flags whether the rejected loser has a
    contradiction other than the one just resolved."""
    x = facade.create({"title": "X", "content": "X note."})["id"]
    y = facade.create({"title": "Y", "content": "Y note."})["id"]
    facade.graph.add_edge(x, y, "contradiction")
    assert facade.resolve(_pair(x, y), x)["hasOtherContradictions"] is False

    p = facade.create({"title": "P", "content": "P note."})["id"]
    q = facade.create({"title": "Q", "content": "Q note."})["id"]
    r = facade.create({"title": "R", "content": "R note."})["id"]
    facade.graph.add_edge(p, q, "contradiction")
    facade.graph.add_edge(q, r, "contradiction")  # q's other contradiction
    assert facade.resolve(_pair(p, q), p)["hasOtherContradictions"] is True  # loser q
