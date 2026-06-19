"""Low-level OpenRouter HTTP (shared seam internals).

OpenRouter is OpenAI-compatible; this is a thin stdlib client used by the
embedder and LLM variants — and re-used by the eval backend. The POST is
injectable (``post``) so everything above it tests offline. Auth/config via env
(``OPENROUTER_API_KEY``, ``OPENROUTER_MODEL``, ``OPENROUTER_EMBED_MODEL``).
"""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Callable

BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_CHAT_MODEL = "openai/gpt-4o-mini"
DEFAULT_EMBED_MODEL = "openai/text-embedding-3-small"

# A POST seam: (url, payload, headers, timeout) -> raw response body (str).
Poster = Callable[[str, dict, dict, int], str]


def default_post(url: str, payload: dict, headers: dict, timeout: int) -> str:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - fixed host
        return resp.read().decode("utf-8")


def _headers(api_key: str) -> dict:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    referer = os.getenv("OPENROUTER_HTTP_REFERER")
    if referer:
        headers["HTTP-Referer"] = referer
    headers["X-Title"] = os.getenv("OPENROUTER_TITLE", "praxis")
    return headers


def _require_key(api_key: str | None) -> str:
    key = api_key if api_key is not None else os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("set OPENROUTER_API_KEY to use the OpenRouter backend")
    return key


def chat_complete(
    messages: list[dict],
    *,
    model: str | None = None,
    api_key: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 1024,
    post: Poster | None = None,
    timeout: int = 120,
) -> str:
    """Return the assistant text for one chat completion."""
    payload = {
        "model": model or os.getenv("OPENROUTER_MODEL", DEFAULT_CHAT_MODEL),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    raw = (post or default_post)(
        f"{BASE_URL}/chat/completions", payload, _headers(_require_key(api_key)), timeout
    )
    return json.loads(raw)["choices"][0]["message"]["content"]


def embed(
    texts: list[str],
    *,
    model: str | None = None,
    api_key: str | None = None,
    post: Poster | None = None,
    timeout: int = 120,
) -> list[list[float]]:
    """Return one embedding vector per input text, order-preserved."""
    payload = {
        "model": model or os.getenv("OPENROUTER_EMBED_MODEL", DEFAULT_EMBED_MODEL),
        "input": texts,
    }
    raw = (post or default_post)(
        f"{BASE_URL}/embeddings", payload, _headers(_require_key(api_key)), timeout
    )
    data = json.loads(raw)["data"]
    return [row["embedding"] for row in data]
