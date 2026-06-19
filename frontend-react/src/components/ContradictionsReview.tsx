import { useMemo, useState } from "react";
import { contradictionPairId } from "../api/contract";
import type { Candidate } from "../types/candidate";

export interface ContradictionPair {
  primary: Candidate;
  rival: Candidate;
}

/**
 * Collapse the per-candidate contradiction references into a unique set of
 * pairs. A↔B is referenced from both sides; we keep one row per logical pair
 * (canonical key = the two ids sorted) and pick the lexicographically smaller
 * id as `primary` for stable ordering.
 */
export function uniqueContradictionPairs(candidates: Candidate[]): ContradictionPair[] {
  const byId = new Map(candidates.map((c) => [c.id, c]));
  const seen = new Set<string>();
  const pairs: ContradictionPair[] = [];
  for (const candidate of candidates) {
    for (const rivalId of candidate.contradictionIds) {
      const rival = byId.get(rivalId);
      if (!rival) continue;
      const key = [candidate.id, rivalId].sort().join("__");
      if (seen.has(key)) continue;
      seen.add(key);
      const [primary, secondary] =
        candidate.id < rival.id ? [candidate, rival] : [rival, candidate];
      pairs.push({ primary, rival: secondary });
    }
  }
  return pairs;
}

function trunc(text: string, max = 32): string {
  return text.length > max ? `${text.slice(0, max)}…` : text;
}

interface ContradictionsReviewProps {
  candidates: Candidate[];
  onResolve: (
    contradictionId: string,
    resolution: "keep_primary" | "keep_rival",
    keepId: string,
    rivalTitle: string,
  ) => Promise<void>;
  onDefer: (primaryTitle: string, rivalTitle: string) => void;
}

export function ContradictionsReview({
  candidates,
  onResolve,
  onDefer,
}: ContradictionsReviewProps) {
  const [pending, setPending] = useState<string | null>(null);
  const pairs = useMemo(() => uniqueContradictionPairs(candidates), [candidates]);

  if (pairs.length === 0) {
    return (
      <p className="muted">
        No contradictions to review — the knowledge base is internally consistent.
      </p>
    );
  }

  return (
    <div className="contradiction-review">
      <p className="muted">
        {pairs.length} contradiction{pairs.length === 1 ? "" : "s"} awaiting review. Keep one
        side or defer to leave both in the queue.
      </p>
      {pairs.map(({ primary, rival }) => {
        const pairId = contradictionPairId(primary.id, rival.id);
        return (
          <div key={pairId} className="contradiction-pair">
            <div className="compare-grid">
              <div className="compare-card">
                <strong>{primary.title}</strong>
                <span className="muted"> · {primary.displayState}</span>
                <p>{primary.content}</p>
                <code>{primary.provenance}</code>
              </div>
              <div className="compare-card rival">
                <strong>{rival.title}</strong>
                <span className="muted"> · {rival.displayState}</span>
                <p>{rival.content}</p>
                <code>{rival.provenance}</code>
              </div>
            </div>
            <div className="action-buttons">
              <button
                type="button"
                className="btn primary"
                disabled={pending === pairId}
                onClick={() => {
                  setPending(pairId);
                  void onResolve(pairId, "keep_primary", primary.id, rival.title).finally(() =>
                    setPending(null),
                  );
                }}
              >
                Keep {trunc(primary.title)}
              </button>
              <button
                type="button"
                className="btn"
                disabled={pending === pairId}
                onClick={() => {
                  setPending(pairId);
                  void onResolve(pairId, "keep_rival", rival.id, rival.title).finally(() =>
                    setPending(null),
                  );
                }}
              >
                Keep {trunc(rival.title)}
              </button>
              <button
                type="button"
                className="btn ghost"
                onClick={() => onDefer(primary.title, rival.title)}
                title="Leave both candidates in the queue for later review"
              >
                Defer
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
