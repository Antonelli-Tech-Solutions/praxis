"""Integration tests for the private, per-login SpacesStore.

Mirrors test_orgs_store.py: skipped unless a database is reachable (PRAXIS_DB_URL
or a resolvable Secrets Manager DSN). Each test uses a unique org_id so runs never
collide. ``spaces`` has a foreign key to ``orgs``, so every test first creates the
owning org via :class:`OrgsStore` before inserting spaces.
"""

from __future__ import annotations

import uuid

import pytest

from knowledge.serve import db

pytestmark = pytest.mark.skipif(
    db.resolve_dsn() is None,
    reason="no Postgres DSN available (set PRAXIS_DB_URL or configure AWS secret)",
)

OWNER_A = "owner-a"
OWNER_B = "owner-b"


@pytest.fixture
def unique_org():
    # A fresh org id per run so the orgs FK insert never collides with leftovers.
    return "test_org_" + uuid.uuid4().hex[:12]


def _stores(org_id: str):
    """Create the owning org and return a SpacesStore over the same connection."""
    from knowledge.serve.orgs_store import OrgsStore
    from knowledge.serve.spaces_store import SpacesStore

    conn = db.connect()
    # spaces.org_id REFERENCES orgs(org_id): the org must exist first.
    OrgsStore(conn).create_org(org_id, "Acme", "s3cret", OWNER_A)
    return SpacesStore(conn)


def test_create_lists_and_owns(unique_org):
    s = _stores(unique_org)
    s.create_space(unique_org, OWNER_A, "alpha", "Alpha space")
    assert s.owns(unique_org, OWNER_A, "alpha")
    # owns is exact: a never-created space is not owned.
    assert not s.owns(unique_org, OWNER_A, "beta")
    spaces = s.list_spaces(unique_org, OWNER_A)
    assert [x["space_id"] for x in spaces] == ["alpha"]
    assert spaces[0]["name"] == "Alpha space"
    assert spaces[0]["created_at"] is not None


def test_create_duplicate_raises(unique_org):
    s = _stores(unique_org)
    s.create_space(unique_org, OWNER_A, "alpha", None)
    with pytest.raises(ValueError):
        s.create_space(unique_org, OWNER_A, "alpha", "again")


def test_list_spaces_ordered_by_space_id(unique_org):
    s = _stores(unique_org)
    for sid in ("zebra", "alpha", "mango"):
        s.create_space(unique_org, OWNER_A, sid, None)
    assert [x["space_id"] for x in s.list_spaces(unique_org, OWNER_A)] == [
        "alpha",
        "mango",
        "zebra",
    ]


def test_spaces_are_private_per_owner(unique_org):
    # Spaces are keyed by owner_sub and never shared across logins: a space one
    # login created is invisible to (and unowned by) another login in the same org.
    s = _stores(unique_org)
    s.create_space(unique_org, OWNER_A, "alpha", None)
    assert s.owns(unique_org, OWNER_A, "alpha")
    assert not s.owns(unique_org, OWNER_B, "alpha")
    assert s.list_spaces(unique_org, OWNER_B) == []


def test_same_slug_distinct_owners_coexist(unique_org):
    # The primary key is (org_id, owner_sub, space_id): two logins may each own a
    # space named "alpha" without colliding.
    s = _stores(unique_org)
    s.create_space(unique_org, OWNER_A, "alpha", "A's alpha")
    s.create_space(unique_org, OWNER_B, "alpha", "B's alpha")
    assert s.owns(unique_org, OWNER_A, "alpha")
    assert s.owns(unique_org, OWNER_B, "alpha")
    assert s.list_spaces(unique_org, OWNER_A)[0]["name"] == "A's alpha"
    assert s.list_spaces(unique_org, OWNER_B)[0]["name"] == "B's alpha"
