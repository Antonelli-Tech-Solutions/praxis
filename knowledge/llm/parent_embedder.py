"""Abstract embedder contract.

Turns text into dense vectors for similarity search and dedup. Variants live in
``embedder_variants/`` (OpenRouter for real runs, a deterministic Fake for
offline tests).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from knowledge.llm.llm_def import Vector


class Embedder(ABC):
    """Embeds text into vectors."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[Vector]:
        """Return one vector per input text, order-preserved."""

    def embed_one(self, text: str) -> Vector:
        """Convenience: embed a single string."""
        return self.embed([text])[0]
