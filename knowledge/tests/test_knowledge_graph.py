"""Tests for the InMemoryGraph variant of KnowledgeGraph."""

from knowledge.knowledge_graph.knowledge_graph_variants.in_memory_graph import (
    InMemoryGraph,
)


def test_write_then_read_roundtrips():
    graph = InMemoryGraph()
    graph.write("first lesson")
    assert "first lesson" in graph.read()


def test_write_appends_does_not_clobber():
    graph = InMemoryGraph()
    graph.write("lesson one")
    graph.write("lesson two")
    content = graph.read()
    assert "lesson one" in content
    assert "lesson two" in content


def test_fresh_graph_is_empty():
    assert InMemoryGraph().read() == ""


def test_create_provisions_empty_graph():
    assert InMemoryGraph.create().read() == ""


def test_read_ignores_context():
    graph = InMemoryGraph()
    graph.write("everything")
    assert graph.read(context="anything") == graph.read()


def test_empty_write_is_noop():
    graph = InMemoryGraph()
    graph.write("   ")
    assert graph.read() == ""
