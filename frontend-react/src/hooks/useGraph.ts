import { useCallback, useEffect, useMemo, useState } from "react";
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
  const [graphSnapshot, setGraphSnapshot] = useState<KnowledgeGraphSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refreshGraph = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const snapshot = await provider.getGraph();
      setGraphSnapshot(snapshot);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setGraphSnapshot(null);
    } finally {
      setLoading(false);
    }
  }, [provider]);

  useEffect(() => {
    void refreshGraph();
  }, [refreshGraph, refreshKey]);

  const graph = useMemo(() => {
    const base = graphSnapshot ?? deriveGraphFromCandidates(candidates);
    return mergeGraphWithCandidates(base, candidates);
  }, [graphSnapshot, candidates]);

  return {
    graph,
    loading,
    error,
    source: graph?.source,
    refreshGraph,
  };
}
