"""Concrete ``Embedder`` implementations."""

from knowledge.llm.embedder_variants.fake_embedder import FakeEmbedder
from knowledge.llm.embedder_variants.openrouter_embedder import OpenRouterEmbedder

__all__ = ["FakeEmbedder", "OpenRouterEmbedder"]
