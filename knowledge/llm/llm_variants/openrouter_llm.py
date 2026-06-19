"""Real LLM via OpenRouter (uses your subscription/key)."""

from __future__ import annotations

from knowledge.llm import openrouter_http
from knowledge.llm.llm_def import ChatMessage
from knowledge.llm.parent_llm import Llm


class OpenRouterLlm(Llm):
    def __init__(self, model: str | None = None, post=None) -> None:
        self.model = model
        self.post = post  # injectable for tests

    def complete(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> str:
        payload = [{"role": m.role, "content": m.content} for m in messages]
        return openrouter_http.chat_complete(
            payload,
            model=self.model,
            temperature=temperature,
            max_tokens=max_tokens,
            post=self.post,
        )
