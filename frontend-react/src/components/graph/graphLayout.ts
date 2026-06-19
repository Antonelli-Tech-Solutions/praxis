import type { CandidateState } from "../../types/candidate";
import type { GraphNode } from "../../types/graph";

export function stateNodeColors(state: CandidateState): {
  bg: string;
  text: string;
  border: string;
} {
  switch (state) {
    case "proposed":
      return {
        bg: "var(--state-proposed-bg)",
        text: "var(--state-proposed-text)",
        border: "var(--state-proposed-border)",
      };
    case "suggested":
      return {
        bg: "var(--state-suggested-bg)",
        text: "var(--state-suggested-text)",
        border: "var(--state-suggested-border)",
      };
    case "active":
      return {
        bg: "var(--state-active-bg)",
        text: "var(--state-active-text)",
        border: "var(--state-active-border)",
      };
    case "decayed":
    case "unrecognized":
      return {
        bg: "var(--state-muted-bg)",
        text: "var(--state-muted-text)",
        border: "var(--state-muted-border)",
      };
    default: {
      const _exhaustive: never = state;
      throw new Error(`Unhandled state: ${_exhaustive}`);
    }
  }
}

export function layoutGraphNodes(nodes: GraphNode[]): Map<string, { x: number; y: number }> {
  const positions = new Map<string, { x: number; y: number }>();
  const cols = Math.max(1, Math.ceil(Math.sqrt(nodes.length)));
  const xGap = 240;
  const yGap = 130;

  nodes.forEach((node, index) => {
    const col = index % cols;
    const row = Math.floor(index / cols);
    positions.set(node.id, { x: col * xGap, y: row * yGap });
  });

  return positions;
}
