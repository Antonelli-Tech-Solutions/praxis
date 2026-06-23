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

interface ContradictionsReviewProps {
  candidates: Candidate[];
  onResolve: (
    contradictionId: string,
    resolution: "keep_primary" | "keep_rival",
    keepId: string,
    rivalTitle: string,
  ) => Promise<void>;
  /** Resolve with a brand-new, user-authored answer (neither side). */
  onResolveCustom?: (contradictionId: string, customText: string) => Promise<void>;
  onDefer: (primaryTitle: string, rivalTitle: string) => void;
}

export function ContradictionsReview({
  candidates,
  onResolve,
  onResolveCustom,
  onDefer,
}: ContradictionsReviewProps) {
  const [pending, setPending] = useState<string | null>(null);
  // Per-pair draft text for the "write your own resolution" box.
  const [customDrafts, setCustomDrafts] = useState<Record<string, string>>({});
  // Deferred pair ids live in the tab itself: deferring moves a pair into the
  // Deferred section (no decision made, nothing persisted server-side) and
  // restoring moves it straight back into the review queue.
  const [deferred, setDeferred] = useState<Set<string>>(new Set());
  const pairs = useMemo(() => uniqueContradictionPairs(candidates), [candidates]);

  if (pairs.length === 0) {
    return (
      <p className="muted">
        No contradictions to review — the knowledge base is internally consistent.
      </p>
    );
  }

  const pairKey = (p: ContradictionPair) => contradictionPairId(p.primary.id, p.rival.id);
  const activePairs = pairs.filter((p) => !deferred.has(pairKey(p)));
  const deferredPairs = pairs.filter((p) => deferred.has(pairKey(p)));

  const defer = (pairId: string, primaryTitle: string, rivalTitle: string) => {
    setDeferred((prev) => new Set(prev).add(pairId));
    onDefer(primaryTitle, rivalTitle);
  };
  const restore = (pairId: string) =>
    setDeferred((prev) => {
      const next = new Set(prev);
      next.delete(pairId);
      return next;
    });

  const renderPair = ({ primary, rival }: ContradictionPair) => {
    const pairId = contradictionPairId(primary.id, rival.id);
    const busy = pending === pairId;
    const choice = (
      candidate: Candidate,
      label: string,
      resolution: "keep_primary" | "keep_rival",
      discardedTitle: string,
      accent: boolean,
    ) => (
      <div className={`compare-card${accent ? " rival" : ""}`}>
        <span className="choice-label">{label}</span>
        <div className="choice-head">
          <strong>{candidate.title}</strong>
          <span className="muted"> · {candidate.displayState}</span>
        </div>
        {/* Many notes have no distinct title — the title IS the full text. Only show
            the body when it actually adds something beyond the title. */}
        {candidate.content.trim() !== candidate.title.trim() && <p>{candidate.content}</p>}
        <code>{candidate.provenance}</code>
        <button
          type="button"
          className="btn primary choice-keep"
          disabled={busy}
          onClick={() => {
            setPending(pairId);
            void onResolve(pairId, resolution, candidate.id, discardedTitle).finally(() =>
              setPending(null),
            );
          }}
        >
          Keep {label}
        </button>
      </div>
    );
    const draft = customDrafts[pairId] ?? "";
    const submitCustom = () => {
      const text = draft.trim();
      if (!text || !onResolveCustom) return;
      setPending(pairId);
      void onResolveCustom(pairId, text).finally(() => setPending(null));
    };
    return (
      <div key={pairId} className="contradiction-pair">
        <div className="compare-grid">
          {choice(primary, "Choice A", "keep_primary", rival.title, false)}
          {choice(rival, "Choice B", "keep_rival", primary.title, true)}
        </div>
        {onResolveCustom && (
          <div className="custom-resolution">
            <label className="choice-label" htmlFor={`custom-${pairId}`}>
              Your own resolution
            </label>
            <p className="muted custom-hint">
              Neither choice fits? Write a fact that settles the dispute — it replaces both
              sides.
            </p>
            <textarea
              id={`custom-${pairId}`}
              className="custom-input"
              rows={2}
              placeholder="e.g. Run migrations automatically on deploy in staging, but require manual approval in production."
              value={draft}
              disabled={busy}
              onChange={(e) =>
                setCustomDrafts((prev) => ({ ...prev, [pairId]: e.target.value }))
              }
            />
            <div className="action-buttons custom-actions">
              <button
                type="button"
                className="btn primary"
                disabled={busy || !draft.trim()}
                onClick={submitCustom}
              >
                Resolve with my answer
              </button>
            </div>
          </div>
        )}
        <div className="action-buttons defer-row">
          <button
            type="button"
            className="btn ghost"
            disabled={busy}
            onClick={() => defer(pairId, primary.title, rival.title)}
            title="Move this contradiction to the Deferred list to decide later"
          >
            Defer — decide later
          </button>
        </div>
      </div>
    );
  };

  return (
    <div className="contradiction-review">
      <p className="muted">
        {activePairs.length} contradiction{activePairs.length === 1 ? "" : "s"} awaiting review.
        Keep one side or defer to decide later.
      </p>
      {activePairs.length === 0 ? (
        <p className="muted">All contradictions deferred — restore one below to review it.</p>
      ) : (
        activePairs.map(renderPair)
      )}

      {deferredPairs.length > 0 && (
        <div className="deferred-section">
          <h3 className="deferred-heading">Deferred ({deferredPairs.length})</h3>
          {deferredPairs.map((p) => {
            const pairId = pairKey(p);
            return (
              <div key={pairId} className="deferred-row">
                <span className="deferred-titles">
                  {p.primary.title} <span className="muted">vs</span> {p.rival.title}
                </span>
                <button
                  type="button"
                  className="btn"
                  onClick={() => restore(pairId)}
                  title="Move this contradiction back into the review queue"
                >
                  Move back to review
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
