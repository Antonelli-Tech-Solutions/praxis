"""Force-supersede a candidate's contradictions instead of just flagging them.

The approved-insight path (a human confirmed the wording in chat) wants the new
note to *win*: where :class:`ConflictFlagger` records a ``contradiction:<id>``
flag for later human resolution, this step turns the same LLM-confirmed
contradiction into an ``overwrite`` decision. The store then resolves it
*non-destructively* (see ``PostgresVectorGraph._overwrite``): the new note is
added as a fresh ``active`` fact and every conflicting fact is rejected with its
text preserved and linked back via a ``contradicted_by`` edge. So no contradictory
pair stays both active, the newest approved truth wins, and no prior wording is
destroyed. This step only *identifies* the conflicts (``update_target_id`` =
nearest, ``supersede_ids`` = the rest); it does not mutate facts itself.

Like :class:`ConflictFlagger` it's best-effort: with no LLM, or if detection
fails, it leaves the decision untouched (a plain ``add``).
"""

from __future__ import annotations

from knowledge.llm.llm_def import ChatMessage
from knowledge.llm.parent_llm import Llm
from knowledge.knowledge_graph.write_policy.parent_write_step import WriteStep
from knowledge.knowledge_graph.write_policy.write_policy_def import WriteDecision

_PROMPT = (
    "Does the NEW note contradict the EXISTING note? "
    "Answer only 'yes' or 'no'.\nEXISTING: {existing}\nNEW: {new}"
)


class ConflictOverwriter(WriteStep):
    """On a confirmed contradiction, mark the conflicts for non-destructive resolution."""

    consumes_candidates = True

    def __init__(self, llm: Llm | None = None) -> None:
        self.llm = llm

    def apply(self, decision: WriteDecision) -> None:
        # A dedup match already won; don't fight it. No LLM => can't detect.
        if self.llm is None or decision.dropped or decision.action != "add":
            return
        conflicts: list[str] = []
        for hit in decision.candidates:
            prompt = _PROMPT.format(existing=hit.fact.text, new=decision.text)
            try:
                answer = self.llm.complete([ChatMessage(role="user", content=prompt)])
            except Exception:
                # Detection unavailable — leave it a plain add (best-effort).
                return
            if answer.strip().lower().startswith("yes"):
                conflicts.append(hit.fact.id)
        if not conflicts:
            return
        # Mark the conflicts for non-destructive resolution by the store: the
        # nearest is the primary loser, the rest are superseded. All are rejected
        # (text preserved) + linked; none is overwritten in place.
        decision.action = "overwrite"
        decision.update_target_id = conflicts[0]
        decision.supersede_ids = conflicts[1:]
