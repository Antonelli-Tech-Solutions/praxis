"""Replay an ``Llm.complete`` call from a committed cassette; record misses when allowed.

``dump_ingest`` drives a real text model for three nondeterministic steps — distill,
same-fact dedup, same-slot conflict — whose phrasing varies run to run. ``CassetteLlm``
wraps any :class:`Llm` so those ``complete`` calls become replayable and deterministic:
record each real response once (locally, with a key) and replay it everywhere else,
letting tests exercise the real pipeline offline with no live calls.

Storage reuses :class:`VerdictCassette` (sha256(model_id + payload) key, committed JSON,
loud miss when recording is off). The cache key is the rendered message content plus the
``response_format`` schema name, so the distill / same_fact / same_slot calls — which
share the same model but ask different questions — never collide on one key. The model id
is the inner LLM's model, so swapping models is a clean miss, never silent staleness.

A miss with recording disabled is a **loud error** (inherited from ``VerdictCassette``),
not a silent fallback: a changed seeded input or model is a new key that must fail until
the cassette is refreshed with a key, never pass on a stale fixture.
"""

from __future__ import annotations

import json
from pathlib import Path

from knowledge.llm.llm_def import ChatMessage
from knowledge.llm.parent_llm import Llm
from knowledge.llm.verdict_cassette import VerdictCassette


def _schema_name(response_format: dict | None) -> str:
    """Stable label for the structured-output schema, to namespace the cache key."""
    if not response_format:
        return ""
    js = response_format.get("json_schema") if isinstance(response_format, dict) else None
    if isinstance(js, dict) and js.get("name"):
        return str(js["name"])
    return ""


class CassetteLlm(Llm):
    """An ``Llm`` that replays ``complete`` from a committed cassette, recording misses when allowed."""

    def __init__(self, inner: Llm, cache_path: Path | str, *, allow_compute: bool) -> None:
        self.inner = inner
        model_id = getattr(inner, "model", None) or inner.__class__.__name__
        self._cassette = VerdictCassette(
            cache_path, model_id=str(model_id), allow_compute=allow_compute
        )

    def complete(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        response_format: dict | None = None,
    ) -> str:
        rendered = "\n".join(f"{m.role}: {m.content}" for m in messages)
        payload = f"schema={_schema_name(response_format)}\n{rendered}"

        def compute() -> dict:
            return {
                "response": self.inner.complete(
                    messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                )
            }

        return self._cassette.verdict(payload, compute)["response"]
