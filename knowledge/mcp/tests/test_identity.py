"""Offline tests for the cached-identity helpers (no real Cognito/network).

We point the cache at a tmp file and assert ``load_identity`` raises a clear
login hint when missing and returns the cached tenant when present.
"""

import json

import pytest

from knowledge.mcp import identity


def test_load_identity_raises_when_cache_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("PRAXIS_MCP_CACHE", str(tmp_path / "mcp.json"))
    with pytest.raises(RuntimeError, match="login"):
        identity.load_identity()


def test_load_identity_returns_tenant_when_present(monkeypatch, tmp_path):
    cache = tmp_path / "mcp.json"
    cache.write_text(
        json.dumps(
            {
                "refresh_token": "rt",
                "sub": "user-1",
                "email": "a@b.com",
                "org_id": "acme",
                "api_base": "http://api.test",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("PRAXIS_MCP_CACHE", str(cache))

    tenant = identity.load_identity()
    assert tenant.sub == "user-1"
    assert tenant.org_id == "acme"
    assert identity.active_org() == "acme"
    assert identity.api_base() == "http://api.test"


def _write_cache(path, **overrides):
    data = {
        "refresh_token": "rt",
        "sub": "user-1",
        "email": "a@b.com",
        "org_id": "acme",
        "api_base": "http://api.test",
    }
    data.update(overrides)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_active_space_env_overrides_cached(monkeypatch, tmp_path):
    """PRAXIS_SPACE pins a space per-process, taking precedence over the cache."""
    cache = tmp_path / "mcp.json"
    _write_cache(cache, space_id="cached-space")
    monkeypatch.setenv("PRAXIS_MCP_CACHE", str(cache))

    monkeypatch.setenv("PRAXIS_SPACE", "env-space")
    assert identity.active_space() == "env-space"

    # Whitespace-only override is ignored -> fall back to the cached value.
    monkeypatch.setenv("PRAXIS_SPACE", "  ")
    assert identity.active_space() == "cached-space"

    # No override at all -> cached value.
    monkeypatch.delenv("PRAXIS_SPACE", raising=False)
    assert identity.active_space() == "cached-space"


def test_active_space_defaults_empty_for_old_cache(monkeypatch, tmp_path):
    """A cache file written before spaces existed (no space_id key) reads as ""."""
    cache = tmp_path / "mcp.json"
    _write_cache(cache)  # no space_id
    monkeypatch.setenv("PRAXIS_MCP_CACHE", str(cache))
    monkeypatch.delenv("PRAXIS_SPACE", raising=False)
    assert identity.active_space() == ""
