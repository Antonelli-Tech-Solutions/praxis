"""Abstract write-policy step.

Each step does one thing to a :class:`WriteDecision` (redact, dedup, flag) and is
composed in order by the store. Steps are independently testable and swappable.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from knowledge.knowledge_graph.write_policy.write_policy_def import StoreView, WriteDecision


class WriteStep(ABC):
    """One stage of the write-time policy pipeline."""

    @abstractmethod
    def apply(self, decision: WriteDecision, store: StoreView) -> None:
        """Mutate ``decision`` in place. Single responsibility per step."""
