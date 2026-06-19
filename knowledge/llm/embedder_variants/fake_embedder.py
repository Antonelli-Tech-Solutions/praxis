"""Deterministic embedder for offline tests.

Hashes each text into a fixed-dimension unit vector — stable across runs and
identical for identical input (so exact-duplicate detection is exercised
deterministically), with no network and no model download. It carries no real
semantics, so semantic-similarity behavior (near-duplicate merge) is only
meaningful with a real embedder.
"""

from __future__ import annotations

import hashlib
import math

from knowledge.llm.llm_def import Vector
from knowledge.llm.parent_embedder import Embedder

_DIM = 32


class FakeEmbedder(Embedder):
    def embed(self, texts: list[str]) -> list[Vector]:
        return [self._vec(t) for t in texts]

    @staticmethod
    def _vec(text: str) -> Vector:
        # Expand a digest into _DIM bytes, scale to [-1, 1], L2-normalize.
        raw = b""
        i = 0
        while len(raw) < _DIM:
            raw += hashlib.sha256(f"{i}:{text}".encode("utf-8")).digest()
            i += 1
        vals = [(b / 127.5) - 1.0 for b in raw[:_DIM]]
        norm = math.sqrt(sum(v * v for v in vals)) or 1.0
        return [v / norm for v in vals]
