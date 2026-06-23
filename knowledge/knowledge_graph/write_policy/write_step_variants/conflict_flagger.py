"""Flag a candidate that contradicts an existing, similar fact.

Reads the store's shared recall pass (``decision.candidates``) and asks an
injected ``Llm`` whether the new text contradicts each candidate; if so, records
a ``contradiction:<id>`` flag (the store keeps the fact but marks it for
human/automated resolution). With no LLM provided the step is inert — conflict
handling is opt-in for this baseline. A deterministic FakeLlm exercises it in
tests. Skipped when the write already merged (``action == "update"``): merge runs
before conflict, and a merged dup needs no conflict check.
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


class ConflictFlagger(WriteStep):
    consumes_candidates = True

    def __init__(self, llm: Llm | None = None) -> None:
        self.llm = llm

    def apply(self, decision: WriteDecision) -> None:
        if self.llm is None or decision.dropped or decision.action == "update":
            return
        for hit in decision.candidates:
            prompt = _PROMPT.format(existing=hit.fact.text, new=decision.text)
            try:
                answer = self.llm.complete([ChatMessage(role="user", content=prompt)])
            except Exception:
                # Detection unavailable (e.g. no API key / network) — skip the
                # check rather than failing the write. Detection is best-effort.
                return
            if answer.strip().lower().startswith("yes"):
                decision.flags.append(f"contradiction:{hit.fact.id}")
