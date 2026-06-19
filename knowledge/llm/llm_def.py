"""Shapes for the LLM/embedding seam."""

from __future__ import annotations

from pydantic import BaseModel


class ChatMessage(BaseModel):
    """One chat turn handed to an ``Llm``."""

    role: str
    content: str


# An embedding is a dense vector; aliased for readability at call sites.
Vector = list[float]
