"""Wire a concrete knowledge trio (graph + ingestor + reader).

Lives in its own module so both the entrypoint (``knowledge.run``) and the
harness (``knowledge.evals.run``) can import it without a circular dependency.
"""

from __future__ import annotations

from knowledge.graph_reader.grapher_reader_variants.whole_file_reader import (
    WholeFileReader,
)
from knowledge.injestion.injestor_variants.prompt_injestor import PromptIngestor
from knowledge.knowledge_graph.knowledge_graph_variants.in_memory_graph import (
    InMemoryGraph,
)
from knowledge.knowledge_graph.parent_knowledge_graph import KnowledgeGraph


def build_trio(graph: KnowledgeGraph | None = None, llm=None):
    """Return a wired ``(graph, ingestor, reader)``.

    Defaults to a fresh in-memory graph (the graph provisions itself via
    ``create``); pass a graph instance to wire a specific substrate.
    """
    graph = graph or InMemoryGraph.create()
    ingestor = PromptIngestor(graph, llm=llm)
    reader = WholeFileReader(graph)
    return graph, ingestor, reader
