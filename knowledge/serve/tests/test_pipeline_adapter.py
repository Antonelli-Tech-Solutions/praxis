"""Tests for pipeline → candidate export adapter."""

from pathlib import Path

from knowledge.injestion.injestion_def import Insight
from knowledge.knowledge_graph.knowledge_graph_def import Fact
from knowledge.knowledge_graph.knowledge_graph_variants.vector_graph import VectorGraph
from knowledge.serve.pipeline_adapter import (
    candidates_from_graph,
    export_pipeline_candidates,
    fact_to_candidate,
    ingest_insights,
)


def test_fact_to_candidate_shapes_contract_fields():
    fact = Fact(
        id="abc123",
        text="Prefer pathlib over os.path for new Python file operations.",
        source="logs/session_20260616.jsonl:201",
        confidence=0.88,
        scope="global",
        observation_count=7,
    )
    candidate = fact_to_candidate(fact)
    assert candidate["id"] == "pipe_abc123"
    assert candidate["provenance"] == "logs/session_20260616.jsonl:201"
    assert candidate["confidenceBreakdown"]["frequency"] == 0.7
    assert candidate["auditTrail"][0]["actor"] == "pipeline"


def test_export_pipeline_candidates_writes_json(tmp_path: Path):
    insights = tmp_path / "insights.json"
    insights.write_text(
        '[{"raw_text": "Use uv run pytest for the test suite.", '
        '"source": "logs/session.jsonl:1", "confidence": 0.9}]',
        encoding="utf-8",
    )
    output = tmp_path / "candidates.json"
    rows = export_pipeline_candidates(insights_path=insights, output_path=output)
    assert len(rows) == 1
    assert output.exists()
    assert rows[0]["content"].startswith("Use uv run pytest")


def test_candidates_from_graph_links_contradictions():
    graph = VectorGraph()
    ingest_insights(
        graph,
        [
            Insight(raw_text="Use explicit error enums in library code."),
            Insight(raw_text="Avoid Box<dyn Error> in public library APIs."),
        ],
    )
    flagged = graph.facts[0]
    flagged.flags.append(f"contradiction:{graph.facts[1].id}")
    candidates = candidates_from_graph(graph)
    assert len(candidates) == 2
    linked = next(c for c in candidates if c["id"] == f"pipe_{flagged.id[:12]}")
    assert linked["contradiction_ids"]
