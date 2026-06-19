"""Tests for the VectorGraph store (offline via FakeEmbedder)."""

from knowledge.knowledge_graph.knowledge_graph_variants.vector_graph import VectorGraph
from knowledge.knowledge_graph.parent_knowledge_graph import KnowledgeGraph
from knowledge.knowledge_graph.parent_searchable_graph import SearchableGraph


def test_is_a_searchable_knowledge_graph():
    g = VectorGraph()
    assert isinstance(g, KnowledgeGraph)
    assert isinstance(g, SearchableGraph)


def test_write_then_read_roundtrips():
    g = VectorGraph()
    g.write("prefer composition over inheritance")
    assert "composition over inheritance" in g.read()


def test_exact_duplicate_is_deduped():
    g = VectorGraph()
    g.write("use uv run pytest")
    g.write("use uv run pytest")  # exact dup -> merged, not added
    assert g.read().count("use uv run pytest") == 1
    assert g._facts[0].observation_count == 2


def test_write_redacts_secrets_and_pii():
    g = VectorGraph()
    g.write("the key is sk-live-SECRET123 and email jane.doe@example.com")
    content = g.read()
    assert "sk-live-SECRET123" not in content
    assert "jane.doe@example.com" not in content


def test_search_returns_best_match_first():
    g = VectorGraph()
    g.write("the deploy script lives at scripts/deploy.sh")
    g.write("the test command is uv run pytest")
    hits = g.search("scripts/deploy.sh", top_k=2)
    assert hits
    assert "deploy.sh" in hits[0].fact.text


def test_empty_write_is_noop():
    g = VectorGraph()
    g.write("   ")
    assert g.read() == ""
