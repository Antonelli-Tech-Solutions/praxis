"""Abstract ingestor contract.

``ingest`` is *concrete* — it runs the same way for every variant: synthesize a
list of :class:`Insight` objects from the raw input, then write each into the
graph. The variable, model-specific step is the abstract :meth:`Ingestor.synthesis`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from knowledge.injestion.injestion_def import Insight
from knowledge.knowledge_graph.parent_knowledge_graph import KnowledgeGraph


class Ingestor(ABC):
    """Distills raw input into the knowledge graph."""

    def __init__(self, graph: KnowledgeGraph) -> None:
        self.graph = graph

    @abstractmethod
    def synthesis(self, raw_input: str, *, source: str | None = None) -> list[Insight]:
        """Transform raw input into structured insights. Variant-defined.

        ``source`` is the document's origin/identifier (e.g. a citation or form
        section). Variants that distill with an LLM may use it as context to
        resolve in-document references; deterministic variants can ignore it.
        """

    def ingest(
        self, raw_input: str, *, state: str = "proposed", source: str | None = None
    ) -> str:
        """Synthesize insights from ``raw_input`` and write each to the graph.

        Concrete and final for the MVP — runs every time. Returns the graph
        content after ingestion for inspection/testing.

        ``state`` is the lifecycle state distilled facts land in. It defaults to
        "proposed": ingestion is a *passive* add (the system distilling raw
        input), so its output is staged, not endorsed. A caller enacting a direct
        user approval passes ``state="active"``.

        ``source`` is threaded both into ``synthesis`` (as distillation context)
        and onto each written fact's provenance.
        """
        insights = self.synthesis(raw_input, source=source)
        for insight in insights:
            # Only thread optional kwargs through when they carry signal: not every
            # graph implementation (in-memory/test doubles) accepts them. ``source``
            # is the persistent store's fact provenance; ``tabular`` flags a
            # table-derived write so the deduper's slot-guard engages downstream.
            kwargs: dict = {"state": state}
            if source is not None:
                kwargs["source"] = source
            if insight.tabular:
                kwargs["tabular"] = True
            self.graph.write(insight.raw_text, **kwargs)
        return self.graph.read()
