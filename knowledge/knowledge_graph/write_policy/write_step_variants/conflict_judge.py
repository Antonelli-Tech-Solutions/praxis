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

The cassette key is ``(model_id, rendered_prompt)``: the payload is the exact prompt
sent to the model, so the judged texts, the prompt wording, and any injected config
all land in the key. A model swap, a prompt edit, or different inputs each produce a
clean miss rather than a stale replay -- the same keying the rubric judge uses.
"""

from __future__ import annotations

import json

from knowledge.llm.llm_def import ChatMessage
from knowledge.llm.parent_llm import Llm
from knowledge.llm.verdict_cassette import VerdictCassette

_PROMPT = (
    "You decide whether two notes about a software project CONTRADICT each other.\n"
    "Two notes contradict ONLY IF they make claims about the same subject and "
    "attribute that cannot both be true at the same time and in the same scope. "
    "If both notes can hold simultaneously they DO NOT contradict — this includes "
    "complementary facts, two valid alternatives, different aspects of the same "
    "thing, and claims scoped to different conditions, components, or times.\n"
    "First give a one-sentence rationale, then set contradicts.\n\n"
    "Examples:\n"
    "EXISTING: Always use tabs for indentation; spaces are forbidden.\n"
    "NEW: Always use spaces for indentation; tabs are forbidden.\n"
    "-> contradicts: true (same attribute, mutually exclusive)\n\n"
    "EXISTING: Rubric grading runs through Claude Code.\n"
    "NEW: Rubric grading is skipped during the offline verify pass.\n"
    "-> contradicts: false (different conditions; both hold at once)\n\n"
    "EXISTING: Insights can be seeded via the ingestor.\n"
    "NEW: Insights can be written directly to the graph.\n"
    "-> contradicts: false (two valid alternatives, not a conflict)\n\n"
    "Now judge this pair:\n"
    "EXISTING: {existing}\n"
    "NEW: {new}"
)

# Structured output: a JSON object (a bare boolean is not a valid json_schema root).
# ``rationale`` comes first so the model reasons before committing to the boolean;
# it's not stored in the cassette (``_compute`` keeps only ``contradicts``).
_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "conflict_verdict",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "rationale": {"type": "string"},
                "contradicts": {"type": "boolean"},
            },
            "required": ["rationale", "contradicts"],
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
        prompt = _PROMPT.format(existing=existing, new=incoming)
        if self.cassette is not None:
            # Key on the exact rendered prompt: a prompt edit or different texts is a
            # clean miss, never a stale replay.
            return self.cassette.verdict(prompt, lambda: self._compute(prompt))["contradicts"]
        if self.llm is not None:
            return self._compute(prompt)["contradicts"]
        return None  # no verdict source -> skip

    def _compute(self, prompt: str) -> dict:
        raw = self.llm.complete(
            [ChatMessage(role="user", content=prompt)],
            response_format=_SCHEMA,
        )
        return {"contradicts": bool(json.loads(raw)["contradicts"])}
