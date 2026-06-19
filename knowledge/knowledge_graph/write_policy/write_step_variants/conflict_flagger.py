"""Flag a candidate that contradicts an existing, similar fact.

Retrieves the most similar existing facts and asks an injected ``Llm`` whether
the new text contradicts them; if so, records a flag (the store keeps the fact
but marks it for human/automated resolution). With no LLM provided the step is
inert — conflict handling is opt-in for this baseline. A deterministic FakeLlm
exercises it in tests.
"""

from __future__ import annotations

from knowledge.llm.llm_def import ChatMessage
from knowledge.llm.parent_llm import Llm
from knowledge.knowledge_graph.write_policy.parent_write_step import WriteStep
from knowledge.knowledge_graph.write_policy.write_policy_def import StoreView, WriteDecision

_PROMPT = (
    "Does the NEW note contradict the EXISTING note? "
    "Answer only 'yes' or 'no'.\nEXISTING: {existing}\nNEW: {new}"
)


class ConflictFlagger(WriteStep):
    def __init__(self, llm: Llm | None = None, similarity_floor: float = 0.6) -> None:
        self.llm = llm
        self.similarity_floor = similarity_floor

    def apply(self, decision: WriteDecision, store: StoreView) -> None:
        if self.llm is None or decision.dropped or decision.action == "update":
            return
        for hit in store.most_similar(decision.text, k=3):
            if hit.score < self.similarity_floor:
                break
            prompt = _PROMPT.format(existing=hit.fact.text, new=decision.text)
            try:
                answer = self.llm.complete([ChatMessage(role="user", content=prompt)])
            except Exception:
                # Detection unavailable (e.g. no API key / network) — skip the
                # check rather than failing the write. Detection is best-effort.
                return
            if answer.strip().lower().startswith("yes"):
                decision.flags.append(f"contradiction:{hit.fact.id}")
