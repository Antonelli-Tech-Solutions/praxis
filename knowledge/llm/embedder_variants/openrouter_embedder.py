"""Real embedder via OpenRouter (uses your subscription/key)."""

from __future__ import annotations

from knowledge.llm import openrouter_http
from knowledge.llm.llm_def import Vector
from knowledge.llm.parent_embedder import Embedder


class OpenRouterEmbedder(Embedder):
    def __init__(self, model: str | None = None, post=None) -> None:
        self.model = model
        self.post = post  # injectable for tests

    def embed(self, texts: list[str]) -> list[Vector]:
        if not texts:
            return []
        return openrouter_http.embed(texts, model=self.model, post=self.post)
