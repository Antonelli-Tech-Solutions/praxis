"""LLM conflict-judge: does the NEW note contradict an EXISTING note?

The precision arbiter for contradiction flagging — no cosine threshold decides
it. Mirrors :class:`MergeJudge`: given the incoming text and an existing
candidate fact, it asks an injected ``Llm`` a tight yes/no question with
structured output. The cassette stores only the method-agnostic
``{"contradicts": bool}``; the contradiction target is a runtime fact id, so the
caller (:class:`ConflictFlagger`) resolves it to the candidate at write time.

Determinism + graceful degradation, mirroring ``MergeJudge``:
- a ``VerdictCassette`` replays committed verdicts offline (loud-miss on a stale one);
- with a live ``llm`` and no cassette, it computes directly (production path);
- with neither, ``contradicts`` returns ``None`` — the caller skips the conflict check.
"""

from __future__ import annotations

import json

from knowledge.llm.llm_def import ChatMessage
from knowledge.llm.parent_llm import Llm
from knowledge.llm.verdict_cassette import VerdictCassette

_PROMPT = (
    "Does the NEW note contradict the EXISTING note? "
    "Set contradicts true if it does, false otherwise.\nEXISTING: {existing}\nNEW: {new}"
)

# Structured output: a JSON object (a bare boolean is not a valid json_schema root).
_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "conflict_verdict",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {"contradicts": {"type": "boolean"}},
            "required": ["contradicts"],
            "additionalProperties": False,
        },
    },
}


class ConflictJudge:
    """Decides whether an incoming note contradicts an existing one."""

    def __init__(
        self, llm: Llm | None = None, cassette: VerdictCassette | None = None
    ) -> None:
        self.llm = llm
        self.cassette = cassette

    def contradicts(self, incoming: str, existing: str) -> bool | None:
        """True/False if a verdict is available; None to skip (no cassette, no llm)."""
        if self.cassette is not None:
            # Ordered pair as the payload, so the key is stable across runs.
            payload = f"{existing}\n||\n{incoming}"
            return self.cassette.verdict(
                payload, lambda: self._compute(incoming, existing)
            )["contradicts"]
        if self.llm is not None:
            return self._compute(incoming, existing)["contradicts"]
        return None  # no verdict source -> skip

    def _compute(self, incoming: str, existing: str) -> dict:
        raw = self.llm.complete(
            [ChatMessage(role="user", content=_PROMPT.format(existing=existing, new=incoming))],
            response_format=_SCHEMA,
        )
        return {"contradicts": bool(json.loads(raw)["contradicts"])}
