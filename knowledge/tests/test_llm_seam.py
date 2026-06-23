"""Tests for the shared embedding/LLM seam (offline)."""

import json
import urllib.error

import pytest

from knowledge.llm import openrouter_http
from knowledge.llm.embedder_variants.fake_embedder import FakeEmbedder
from knowledge.llm.embedder_variants.openrouter_embedder import OpenRouterEmbedder
from knowledge.llm.llm_def import ChatMessage
from knowledge.llm.llm_variants.fake_llm import FakeLlm
from knowledge.llm.llm_variants.openrouter_llm import OpenRouterLlm


def test_fake_embedder_is_deterministic_and_normalized():
    e = FakeEmbedder()
    v1 = e.embed_one("hello")
    v2 = e.embed_one("hello")
    assert v1 == v2  # deterministic
    assert v1 != e.embed_one("world")  # input-sensitive
    norm = sum(x * x for x in v1) ** 0.5
    assert abs(norm - 1.0) < 1e-9  # unit length
    assert len(e.embed(["a", "b", "c"])) == 3  # one per text


def test_fake_llm_scripts_and_echoes():
    llm = FakeLlm(scripted={"ping": "pong"})
    assert llm.complete([ChatMessage(role="user", content="ping")]) == "pong"
    assert llm.complete([ChatMessage(role="user", content="hi")]) == "hi"  # echo default


def test_openrouter_embedder_parses_vectors(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")

    def fake_post(url, payload, headers, timeout):
        assert url.endswith("/embeddings")
        return json.dumps({"data": [{"embedding": [0.1, 0.2]} for _ in payload["input"]]})

    vecs = OpenRouterEmbedder(post=fake_post).embed(["a", "b"])
    assert vecs == [[0.1, 0.2], [0.1, 0.2]]


def test_openrouter_llm_parses_text(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")

    def fake_post(url, payload, headers, timeout):
        assert url.endswith("/chat/completions")
        return json.dumps({"choices": [{"message": {"content": "ok"}}]})

    out = OpenRouterLlm(post=fake_post).complete([ChatMessage(role="user", content="hi")])
    assert out == "ok"


def test_default_post_retries_transient_then_succeeds(monkeypatch):
    monkeypatch.setattr(openrouter_http.time, "sleep", lambda _s: None)  # no real backoff
    calls = {"n": 0}

    def flaky(url, payload, headers, timeout):
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionResetError("WinError 10054")  # transient (OSError)
        return "ok"

    monkeypatch.setattr(openrouter_http, "_request_once", flaky)
    assert openrouter_http.default_post("u", {}, {}, 5) == "ok"
    assert calls["n"] == 3  # two failures, third attempt wins


def test_default_post_retries_on_5xx_then_raises_after_max(monkeypatch):
    monkeypatch.setattr(openrouter_http.time, "sleep", lambda _s: None)
    calls = {"n": 0}

    def always_503(url, payload, headers, timeout):
        calls["n"] += 1
        raise urllib.error.HTTPError(url, 503, "Service Unavailable", {}, None)

    monkeypatch.setattr(openrouter_http, "_request_once", always_503)
    with pytest.raises(urllib.error.HTTPError):
        openrouter_http.default_post("u", {}, {}, 5)
    assert calls["n"] == openrouter_http._MAX_ATTEMPTS  # exhausted retries


def test_default_post_does_not_retry_client_error(monkeypatch):
    monkeypatch.setattr(openrouter_http.time, "sleep", lambda _s: None)
    calls = {"n": 0}

    def always_400(url, payload, headers, timeout):
        calls["n"] += 1
        raise urllib.error.HTTPError(url, 400, "Bad Request", {}, None)

    monkeypatch.setattr(openrouter_http, "_request_once", always_400)
    with pytest.raises(urllib.error.HTTPError):
        openrouter_http.default_post("u", {}, {}, 5)
    assert calls["n"] == 1  # fail fast, no retry on 4xx
