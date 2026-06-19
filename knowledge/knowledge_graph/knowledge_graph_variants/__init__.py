"""Concrete ``KnowledgeGraph`` implementations."""

from knowledge.knowledge_graph.knowledge_graph_variants.in_memory_graph import (
    InMemoryGraph,
)
from knowledge.knowledge_graph.knowledge_graph_variants.vector_graph import VectorGraph

__all__ = ["InMemoryGraph", "VectorGraph"]
