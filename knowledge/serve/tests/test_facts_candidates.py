"""Unit tests for the FactsCandidates facade over the facts spine.

These build the facade directly with a deterministic FakeEmbedder and a no-LLM
write policy ([Redactor(), Deduper()]), so they need a Postgres DSN but make no
network/LLM calls. Each test uses a unique throwaway org so runs never collide.
"""

from __future__ import annotations

import pytest

from knowledge.knowledge_graph.knowledge_graph_def import Claim
from knowledge.knowledge_graph.write_policy.write_step_variants import Deduper, Redactor
from knowledge.llm.embedder_variants.fake_embedder import FakeEmbedder
from knowledge.serve import db
from knowledge.serve.facts_candidates import FactsCandidates, PromotionError

pytestmark = pytest.mark.skipif(
    db.resolve_dsn() is None,
    reason="no Postgres DSN available (set PRAXIS_DB_URL or configure AWS secret)",
)

USER = "dev-user"


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


def test_reject_decays(facade):
    cid = facade.create({"title": "T", "content": "Some noisy candidate text."})["id"]
    rejected = facade.reject(cid, reason="noise")
    assert rejected["state"] == "decayed"
    assert facade.get(cid)["state"] == "decayed"


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

    clusters = facade.contradictions()
    assert len(clusters) == 1
    cluster = clusters[0]
    assert {m["id"] for m in cluster["members"]} == {a, b}
    pair = cluster["pairs"][0]
    assert pair["id"] == f"{min(a, b)}__{max(a, b)}"
    assert {pair["a"]["id"], pair["b"]["id"]} == {a, b}

    kept = facade.resolve(pair["id"], a)
    assert kept["id"] == a
    assert kept["state"] == "active"
    assert facade.get(b)["state"] == "decayed"
    # The edge is gone, so no pair remains.
    assert facade.contradictions() == []


def _slot_claim(subject: str, attribute: str, value: str) -> Claim:
    return Claim(subject=subject, attribute=attribute, value=value, functional=True)


def test_three_facts_on_one_slot_form_one_cluster(facade):
    a = facade.create({"title": "A", "content": "Voltaic pile invented in 1799."})["id"]
    b = facade.create({"title": "B", "content": "Voltaic pile invented in 1800."})["id"]
    c = facade.create({"title": "C", "content": "Voltaic pile invented in 1801."})["id"]
    # Same functional slot for all three -> they belong in one cluster.
    for fid, year in ((a, "1799"), (b, "1800"), (c, "1801")):
        facade.graph._persist_claims(fid, [_slot_claim("Voltaic pile", "invention year", year)])
    # Pairwise contradiction edges among the three.
    facade.graph.add_edge(a, b, "contradiction")
    facade.graph.add_edge(a, c, "contradiction")
    facade.graph.add_edge(b, c, "contradiction")

    clusters = facade.contradictions()
    assert len(clusters) == 1
    cluster = clusters[0]
    assert {m["id"] for m in cluster["members"]} == {a, b, c}
    assert cluster["slot"] == {"subject": "voltaic pile", "attribute": "invention year"}
    assert {m["value"] for m in cluster["members"]} == {"1799", "1800", "1801"}
    # Resolving one member keeps it via the existing per-pair resolve endpoint.
    pair = cluster["pairs"][0]
    kept_id = pair["a"]["id"]
    facade.resolve(pair["id"], kept_id)
    assert facade.get(kept_id)["state"] == "active"


def test_two_slots_form_two_clusters(facade):
    a = facade.create({"title": "A", "content": "Pile invented 1799."})["id"]
    b = facade.create({"title": "B", "content": "Pile invented 1800."})["id"]
    c = facade.create({"title": "C", "content": "Use tabs."})["id"]
    d = facade.create({"title": "D", "content": "Use spaces."})["id"]
    facade.graph._persist_claims(a, [_slot_claim("pile", "year", "1799")])
    facade.graph._persist_claims(b, [_slot_claim("pile", "year", "1800")])
    facade.graph._persist_claims(c, [_slot_claim("indentation", "style", "tabs")])
    facade.graph._persist_claims(d, [_slot_claim("indentation", "style", "spaces")])
    facade.graph.add_edge(a, b, "contradiction")
    facade.graph.add_edge(c, d, "contradiction")

    clusters = facade.contradictions()
    assert len(clusters) == 2
    member_sets = sorted([{m["id"] for m in cl["members"]} for cl in clusters], key=sorted)
    assert {a, b} in member_sets
    assert {c, d} in member_sets


def test_single_pair_is_cluster_of_two(facade):
    a = facade.create({"title": "A", "content": "Use tabs for indentation."})["id"]
    b = facade.create({"title": "B", "content": "Use spaces for indentation."})["id"]
    facade.graph.add_edge(a, b, "contradiction")

    clusters = facade.contradictions()
    assert len(clusters) == 1
    cluster = clusters[0]
    assert {m["id"] for m in cluster["members"]} == {a, b}
    # No claims stored -> no slot, degrades to a per-pair cluster.
    assert cluster["slot"] is None
    assert len(cluster["pairs"]) == 1

    # Resolving the single underlying pair uses the existing endpoint.
    kept = facade.resolve(cluster["pairs"][0]["id"], a)
    assert kept["id"] == a and kept["state"] == "active"
    assert facade.get(b)["state"] == "decayed"
    assert facade.contradictions() == []


def test_resolve_custom_decays_both_and_creates_active(facade):
    a = facade.create({"title": "A", "content": "Store timestamps in UTC."})["id"]
    b = facade.create({"title": "B", "content": "Store timestamps in local time."})["id"]
    facade.graph.add_edge(a, b, "contradiction")
    pair_id = f"{min(a, b)}__{max(a, b)}"

    new = facade.resolve_custom(pair_id, "Store timestamps in UTC, render in local time.")
    assert new["state"] == "active"
    assert new["id"] not in (a, b)
    assert new["content"] == "Store timestamps in UTC, render in local time."
    assert facade.get(a)["state"] == "decayed"
    assert facade.get(b)["state"] == "decayed"
    assert facade.contradictions() == []
