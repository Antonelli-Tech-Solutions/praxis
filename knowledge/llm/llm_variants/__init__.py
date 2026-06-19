"""Concrete ``Llm`` implementations."""

from knowledge.llm.llm_variants.fake_llm import FakeLlm
from knowledge.llm.llm_variants.openrouter_llm import OpenRouterLlm

__all__ = ["FakeLlm", "OpenRouterLlm"]
