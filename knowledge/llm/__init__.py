"""Shared embedding/LLM seam used across the knowledge pipeline.

Abstract ``Embedder`` and ``Llm`` contracts with OpenRouter (real) and Fake
(deterministic, offline) variants. Core knowledge code depends on these
interfaces, never on the eval harness.
"""

from knowledge.llm.parent_embedder import Embedder
from knowledge.llm.parent_llm import Llm

__all__ = ["Embedder", "Llm"]
