import type { KnowledgeGraphSnapshot } from "../../types/graph";

interface GraphSummaryProps {
  graph: KnowledgeGraphSnapshot;
}

export function GraphSummary({ graph }: GraphSummaryProps) {
  const contradictionCount = graph.edges.filter((e) => e.kind === "contradiction").length;
  const supportCount = graph.edges.filter((e) => e.kind === "support").length;
  const summary = `${graph.nodes.length} nodes, ${graph.edges.length} edges (${contradictionCount} contradictions, ${supportCount} support)`;

  return (
    <div className="graph-summary" role="img" aria-label={summary}>
      <span className="graph-summary__label">Graph snapshot</span>
      <p className="graph-summary__text">{summary}</p>
      <p className="muted graph-summary__source">Source: {graph.source}</p>
    </div>
  );
}
