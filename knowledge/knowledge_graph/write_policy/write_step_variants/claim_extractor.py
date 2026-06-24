"""Write-time extraction of atomic (subject, attribute, value) claims.

The front of the structural contradiction path. Each incoming fact is decomposed
into atomic claims, each tagged ``functional`` (single-valued for its subject) or
not. The detector (``ClaimConflictDetector``) then flags a contradiction only when
two facts share a subject + functional attribute with incompatible values — so the
quality of this extraction is what makes detection precise.

``ClaimExtractionJudge`` mirrors ``AspectJudge``/``ConflictJudge``: structured
output over the LLM seam, replayed offline from a ``VerdictCassette`` (keyed by the
fact text), graceful skip when no source. ``ClaimExtractor`` is the write step that
attaches the extracted claims to the decision (persisted to the ``claims`` table).

Precision-first: extraction returns no claims rather than guesses when uncertain,
so the detector simply has nothing to flag (a missed conflict beats a false one).
"""

from __future__ import annotations

import json

from knowledge.knowledge_graph.knowledge_graph_def import Claim
from knowledge.knowledge_graph.write_policy.parent_write_step import WriteStep
from knowledge.knowledge_graph.write_policy.write_policy_def import WriteDecision
from knowledge.llm.llm_def import ChatMessage
from knowledge.llm.parent_llm import Llm
from knowledge.llm.verdict_cassette import VerdictCassette

_PROMPT = (
    "Decompose the NOTE into atomic factual claims as (subject, attribute, value).\n"
    "- subject: the canonical entity the claim is INHERENTLY about. An invention's "
    "year belongs to the invention (subject='voltaic pile', attribute='invention "
    "year'), NOT to the inventor. Use a STABLE canonical name; for a piece's own "
    "stylistic/production constants use subjects like 'video:audio', 'video:visual', "
    "'video:editing', 'video:structure'.\n"
    "- attribute: the specific property (e.g. 'invention year', 'background color').\n"
    "- value: the asserted value, normalized (years as the bare number).\n"
    "- functional: true if the attribute can have only ONE correct value for that "
    "subject (a birth year, an event's year, a nationality) -> a different value is a "
    "contradiction. false if it is naturally MULTI-valued (a person's discoveries, "
    "roles held over time, a list of metals) -> different values coexist.\n"
    "Emit only claims actually asserted; keep attributes specific so unrelated facts "
    "don't collide. Return an empty list if the note makes no checkable claim.\n"
    "NOTE: {note}"
)

# Structured output: a list of claim objects.
_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "claims",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "claims": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "subject": {"type": "string"},
                            "attribute": {"type": "string"},
                            "value": {"type": "string"},
                            "functional": {"type": "boolean"},
                        },
                        "required": ["subject", "attribute", "value", "functional"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["claims"],
            "additionalProperties": False,
        },
    },
}


class ClaimExtractionJudge:
    """Extracts atomic (subject, attribute, value) claims from a note (or None to skip)."""

    def __init__(
        self, llm: Llm | None = None, cassette: VerdictCassette | None = None
    ) -> None:
        self.llm = llm
        self.cassette = cassette

    def extract(self, note: str) -> list[Claim] | None:
        """Claims for ``note`` if a source is available; None to skip (no cassette, no llm)."""
        if self.cassette is not None:
            raw = self.cassette.verdict(note, lambda: self._compute(note))
            return self._to_claims(raw)
        if self.llm is not None:
            return self._to_claims(self._compute(note))
        return None  # no source -> skip

    def _compute(self, note: str) -> dict:
        raw = self.llm.complete(
            [ChatMessage(role="user", content=_PROMPT.format(note=note))],
            response_format=_SCHEMA,
        )
        # Persist the method-agnostic dict in the cassette; coerce to Claims on read.
        return {"claims": json.loads(raw)["claims"]}

    @staticmethod
    def _to_claims(raw: dict) -> list[Claim]:
        out: list[Claim] = []
        for c in raw.get("claims", []):
            try:
                out.append(
                    Claim(
                        subject=str(c["subject"]),
                        attribute=str(c["attribute"]),
                        value=str(c["value"]),
                        functional=bool(c["functional"]),
                    )
                )
            except (KeyError, TypeError):
                continue  # precision-first: drop a malformed claim, don't fail the write
        return out


class ClaimExtractor(WriteStep):
    """Attach extracted (subject, attribute, value) claims to the incoming note."""

    consumes_candidates = False  # extracts from the new note; needs no existing candidates

    def __init__(self, judge: ClaimExtractionJudge | None = None) -> None:
        self.judge = judge

    def apply(self, decision: WriteDecision) -> None:
        if self.judge is None or decision.dropped:
            return
        try:
            claims = self.judge.extract(decision.text)
        except Exception:
            # Extraction unavailable (e.g. no API key / network) — best-effort, leave
            # the note without claims rather than failing the write.
            return
        if claims:
            decision.claims = list(claims)
