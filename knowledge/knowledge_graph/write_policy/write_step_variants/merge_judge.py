"""LLM merge-judge: do two notes record the SAME lesson, just phrased differently?

The precision arbiter for semantic dedup — no cosine threshold decides the merge.
Given the incoming text and an existing candidate fact, it asks an injected ``Llm`` a
tight yes/no question. The EXISTING fact is the verbatim survivor (the judge selects,
it never rewrites), so the answer the cassette stores is just ``same_lesson``; the
surviving id is the candidate, resolved by the caller at write time.

Determinism + graceful degradation, mirroring ``ConflictFlagger``:
- a ``VerdictCassette`` replays committed verdicts offline (loud-miss on a stale one);
- with a live ``llm`` and no cassette, it computes directly (production path);
- with neither, ``same_lesson`` returns ``None`` — the caller skips the semantic merge
  (exact-dedup still applies).
"""

from __future__ import annotations

from knowledge.llm.llm_def import ChatMessage
from knowledge.llm.parent_llm import Llm
from knowledge.llm.verdict_cassette import VerdictCassette

_PROMPT = (
    "Do these two notes record the SAME lesson or rule, just phrased differently? "
    "Answer only 'yes' or 'no'.\nEXISTING: {existing}\nNEW: {new}"
)


class MergeJudge:
    """Decides whether an incoming note duplicates an existing one (same lesson)."""

    def __init__(
        self, llm: Llm | None = None, cassette: VerdictCassette | None = None
    ) -> None:
        self.llm = llm
        self.cassette = cassette

    def same_lesson(self, incoming: str, existing: str) -> bool | None:
        """True/False if a verdict is available; None to skip (no cassette, no llm)."""
        if self.cassette is not None:
            # Ordered pair as the payload, so the key is stable across runs.
            payload = f"{existing}\n||\n{incoming}"
            return self.cassette.verdict(payload, lambda: self._compute(incoming, existing))[
                "same_lesson"
            ]
        if self.llm is not None:
            return self._compute(incoming, existing)["same_lesson"]
        return None  # no verdict source -> skip

    def _compute(self, incoming: str, existing: str) -> dict:
        answer = self.llm.complete(
            [ChatMessage(role="user", content=_PROMPT.format(existing=existing, new=incoming))]
        )
        return {"same_lesson": answer.strip().lower().startswith("yes")}
