import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  type ApiDataProviderAuth,
  type FoldInResult,
  type OrgSource,
  type SourceFactGroup,
  type SourceFacts,
  foldIn,
  getSourceFacts,
  listOrgSources,
} from "../api/apiClient";
import {
  defaultSelection,
  groupCheckState,
  selectedFactIds,
  toggleFact,
  toggleGroup,
} from "./foldInSelection";

interface SourceFoldInProps {
  apiBaseUrl: string;
  auth?: string | ApiDataProviderAuth;
  /** Called after a successful fold-in so the dashboard can refresh its graph. */
  onFolded?: () => void;
  /** Route the user to the contradictions view when conflicts are returned. */
  onViewContradictions?: () => void;
}

/** A pickable source: a member's live graph, or one of their saved snapshots. */
interface SourceOption {
  value: string; // unique select value: `${userId}::${source}`
  userId: string;
  source: string; // "live" | "snapshot:<name>"
  label: string;
  isSelf: boolean;
}

function buildOptions(sources: OrgSource[]): SourceOption[] {
  const options: SourceOption[] = [];
  for (const s of sources) {
    const who = s.isSelf ? `${s.userId} (you)` : s.userId;
    options.push({
      value: `${s.userId}::live`,
      userId: s.userId,
      source: "live",
      label: `${who} — live graph`,
      isSelf: s.isSelf,
    });
    for (const snap of s.snapshots) {
      options.push({
        value: `${s.userId}::snapshot:${snap}`,
        userId: s.userId,
        source: `snapshot:${snap}`,
        label: `${who} — snapshot "${snap}"`,
        isSelf: s.isSelf,
      });
    }
  }
  return options;
}

/** Group checkbox that reflects checked / indeterminate / unchecked. */
function GroupCheckbox({
  group,
  selected,
  onToggle,
}: {
  group: SourceFactGroup;
  selected: ReadonlySet<string>;
  onToggle: () => void;
}) {
  const ref = useRef<HTMLInputElement>(null);
  const state = groupCheckState(group, selected);
  useEffect(() => {
    if (ref.current) ref.current.indeterminate = state === "indeterminate";
  }, [state]);
  return (
    <input
      ref={ref}
      type="checkbox"
      checked={state === "checked"}
      onChange={onToggle}
      aria-label={`Select all facts in ${group.label}`}
    />
  );
}

/** Browse another source's graph and fold selected skills into your own. */
export function SourceFoldIn({
  apiBaseUrl,
  auth,
  onFolded,
  onViewContradictions,
}: SourceFoldInProps) {
  const [open, setOpen] = useState(false);
  const [options, setOptions] = useState<SourceOption[]>([]);
  const [picked, setPicked] = useState<string>("");
  const [facts, setFacts] = useState<SourceFacts | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<FoldInResult | null>(null);

  const current = useMemo(
    () => options.find((o) => o.value === picked) ?? null,
    [options, picked],
  );

  const refreshSources = useCallback(async () => {
    try {
      const sources = await listOrgSources(apiBaseUrl, auth);
      setOptions(buildOptions(sources));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, [apiBaseUrl, auth]);

  useEffect(() => {
    if (open) void refreshSources();
  }, [open, refreshSources]);

  async function loadFacts(option: SourceOption) {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const data = await getSourceFacts(apiBaseUrl, option.userId, option.source, auth);
      setFacts(data);
      setSelected(defaultSelection(data.groups));
      setExpanded(new Set());
    } catch (err) {
      setFacts(null);
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  function handlePick(value: string) {
    setPicked(value);
    setFacts(null);
    setSelected(new Set());
    setResult(null);
    const option = options.find((o) => o.value === value);
    if (option) void loadFacts(option);
  }

  function handleToggleGroup(group: SourceFactGroup) {
    setSelected((prev) => toggleGroup(group, prev));
  }

  function handleToggleFact(factId: string) {
    setSelected((prev) => toggleFact(factId, prev));
  }

  function handleExpand(key: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  async function handleFoldIn() {
    if (!current || !facts) return;
    const ids = selectedFactIds(facts.groups, selected);
    if (ids.length === 0) {
      setError("Select at least one skill or fact to fold in.");
      return;
    }
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const res = await foldIn(apiBaseUrl, current.userId, current.source, ids, auth);
      setResult(res);
      onFolded?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  const selectedCount = facts ? selectedFactIds(facts.groups, selected).length : 0;

  return (
    <section className="eval-runner">
      <header className="eval-runner__head">
        <button
          type="button"
          className="eval-runner__collapse"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
        >
          {open ? "▾" : "▸"}{" "}
          <span className="eval-runner__title">Browse sources &amp; fold in skills</span>
        </button>
        <span className="eval-runner__hint">
          Pick a teammate&apos;s graph or snapshot, choose skills, and fold them into your
          own graph.
        </span>
      </header>

      {open ? (
        <>
          <div className="eval-runner__row">
            <label className="eval-runner__field">
              <span>Source</span>
              <select
                value={picked}
                onChange={(e) => handlePick(e.target.value)}
                disabled={busy || options.length === 0}
              >
                {options.length === 0 ? (
                  <option value="">No sources available</option>
                ) : (
                  <>
                    <option value="">Select a source…</option>
                    {options.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </>
                )}
              </select>
            </label>
          </div>

          {facts && facts.groups.length > 0 ? (
            <div className="eval-runner__row">
              <ul className="fold-in__groups">
                {facts.groups.map((group) => {
                  const isExpanded = expanded.has(group.key);
                  return (
                    <li key={group.key} className="fold-in__group">
                      <div className="fold-in__group-head">
                        <label className="fold-in__group-label">
                          <GroupCheckbox
                            group={group}
                            selected={selected}
                            onToggle={() => handleToggleGroup(group)}
                          />
                          <span className="fold-in__group-name">{group.label}</span>
                          <span className="fold-in__group-count">
                            ({group.facts.length})
                          </span>
                        </label>
                        <button
                          type="button"
                          className="link-button"
                          onClick={() => handleExpand(group.key)}
                          aria-expanded={isExpanded}
                        >
                          {isExpanded ? "Hide facts" : "Override facts"}
                        </button>
                      </div>
                      {isExpanded ? (
                        <ul className="fold-in__facts">
                          {group.facts.map((fact) => (
                            <li key={fact.id} className="fold-in__fact">
                              <label className="fold-in__fact-label">
                                <input
                                  type="checkbox"
                                  checked={selected.has(fact.id)}
                                  onChange={() => handleToggleFact(fact.id)}
                                />
                                <span>{fact.text}</span>
                              </label>
                            </li>
                          ))}
                        </ul>
                      ) : null}
                    </li>
                  );
                })}
              </ul>
            </div>
          ) : null}

          {facts && facts.groups.length === 0 ? (
            <p className="eval-runner__hint">This source has no facts to fold in.</p>
          ) : null}

          {facts ? (
            <div className="eval-runner__row">
              <div className="eval-runner__actions">
                <button
                  type="button"
                  className="btn primary"
                  onClick={handleFoldIn}
                  disabled={busy || selectedCount === 0}
                  title="Fold the selected skills into your own graph"
                >
                  {busy
                    ? "Working…"
                    : `Fold into my graph (${selectedCount} fact${selectedCount === 1 ? "" : "s"})`}
                </button>
              </div>
            </div>
          ) : null}

          {error ? <p className="eval-runner__error">{error}</p> : null}

          {result ? (
            <div className="eval-runner__loaded">
              <p>
                Folded {result.folded}, deduped {result.deduped}, conflicts{" "}
                {result.conflicts.length}.
              </p>
              {result.conflicts.length > 0 ? (
                <p>
                  Some folded facts contradict your existing graph.{" "}
                  {onViewContradictions ? (
                    <button
                      type="button"
                      className="link-button"
                      onClick={onViewContradictions}
                    >
                      Review contradictions
                    </button>
                  ) : (
                    "Open the Contradictions tab to resolve them."
                  )}
                </p>
              ) : null}
            </div>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
