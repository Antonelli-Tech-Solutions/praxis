import { useCallback, useEffect, useState } from "react";
import type { DataProvider } from "../api/dataProvider";
import {
  deriveGraphFromCandidates,
  mergeGraphWithCandidates,
} from "../api/graphModel";
import type { Candidate } from "../types/candidate";
import type { KnowledgeGraphSnapshot } from "../types/graph";

export function useGraph(
  provider: DataProvider,
  candidates: Candidate[],
  refreshKey: number,
) {
  const [graph, setGraph] = useState<KnowledgeGraphSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refreshGraph = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const snapshot = await provider.getGraph();
      setGraph(mergeGraphWithCandidates(snapshot, candidates));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setGraph(mergeGraphWithCandidates(deriveGraphFromCandidates(candidates), candidates));
    } finally {
      setLoading(false);
    }
  }, [provider, candidates]);

  useEffect(() => {
    void refreshGraph();
  }, [refreshGraph, refreshKey]);

  return {
    graph,
    loading,
    error,
    source: graph?.source,
    refreshGraph,
  };
}
