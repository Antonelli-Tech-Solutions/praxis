"""Deterministic LLM for offline tests.

Returns scripted replies (by exact prompt match or a default), or echoes the
last user message. No network.
"""

from __future__ import annotations

from knowledge.llm.llm_def import ChatMessage
from knowledge.llm.parent_llm import Llm


class FakeLlm(Llm):
    def __init__(self, scripted: dict[str, str] | None = None, default: str = "") -> None:
        self.scripted = scripted or {}
        self.default = default
        self.calls: list[list[ChatMessage]] = []

    def complete(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        response_format: dict | None = None,  # accepted for parity; scripted replies ignore it
    ) -> str:
        self.calls.append(messages)
        last_user = next(
            (m.content for m in reversed(messages) if m.role == "user"), ""
        )
        if last_user in self.scripted:
            return self.scripted[last_user]
        return self.default or last_user
