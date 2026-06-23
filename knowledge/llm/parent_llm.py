"""Abstract LLM contract for non-agent uses (distillation, conflict checks).

This is NOT the agent under eval (that stays real Claude Code). It is the cheap
text-in/text-out model used inside the knowledge pipeline. Variants live in
``llm_variants/``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from knowledge.llm.llm_def import ChatMessage


class Llm(ABC):
    """A chat-style text model."""

    @abstractmethod
    def complete(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        response_format: dict | None = None,
    ) -> str:
        """Return the assistant's reply text for ``messages``.

        ``response_format`` is an optional OpenAI-style structured-output spec (e.g.
        a ``json_schema`` object); when set, the reply is constrained to that schema.
        """
