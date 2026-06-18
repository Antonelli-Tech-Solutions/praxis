"""Tests for the WholeFileReader variant of GraphReader."""

from knowledge.graph_reader.grapher_reader_variants.whole_file_reader import (
    WholeFileReader,
    as_claude_tool,
)
from knowledge.knowledge_graph.knowledge_graph_variants.in_memory_graph import (
    InMemoryGraph,
)


def _graph_with(*lines):
    graph = InMemoryGraph()
    for line in lines:
        graph.write(line)
    return graph


def test_synthesis_returns_single_whole_graph_request():
    reader = WholeFileReader(_graph_with("x"))
    requests = reader.synthesis("any context")
    assert len(requests) == 1


def test_read_returns_full_graph():
    reader = WholeFileReader(_graph_with("alpha", "beta"))
    content = reader.read()
    assert "alpha" in content and "beta" in content


def test_claude_tool_adapter_returns_contents():
    reader = WholeFileReader(_graph_with("tool-visible"))
    tool = as_claude_tool(reader)
    assert tool["name"] == "read_knowledge"
    assert "tool-visible" in tool["func"]()
