import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  type ApiDataProviderAuth,
  type FoldInMode,
  type FoldInResult,
  type OrgSource,
  type SourceFactGroup,
  type SourceFacts,
  foldIn,
  getSnapshotFacts,
  listOrgSources,
  mountSnapshot,
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
  /** When rendered inside a modal: always-open body, no collapse header. */
  embedded?: boolean;
}

/** A pickable snapshot: a member's saved snapshot (own or another's). */
interface SnapshotOption {
  value: string; // unique select value: `${userId}::${snapshot}`
  userId: string;
  snapshot: string;
  label: string;
  isSelf: boolean;
}

/** Flatten every member's snapshots (own + others) into a single option list. */
function buildOptions(sources: OrgSource[]): SnapshotOption[] {
  const options: SnapshotOption[] = [];
  for (const s of sources) {
    const name = s.username || s.userId; // prefer the display name over the raw id
    const who = s.isSelf ? `${name} (me)` : name;
    for (const snap of s.snapshots) {
      const nodes = `${snap.count} node${snap.count === 1 ? "" : "s"}`;
      options.push({
        value: `${s.userId}::${snap.name}`,
        userId: s.userId,
        snapshot: snap.name,
        label: `${who} / ${snap.name} (${nodes})`,
        isSelf: s.isSelf,
      });
    }
  }
  return options;
}

/** Folder checkbox that reflects checked / indeterminate / unchecked. */
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
      className="eval-runner__entry-check"
      checked={state === "checked"}
      onChange={onToggle}
      aria-label={`Select all facts in ${group.label}`}
    />
  );
}

/** Browse a teammate's snapshot and fold selected folders into your own graph. */
export function SourceFoldIn({
  apiBaseUrl,
  auth,
  onFolded,
  onViewContradictions,
  embedded,
}: SourceFoldInProps) {
  const [open, setOpen] = useState(false);
  const isOpen = embedded || open;
  const [options, setOptions] = useState<SnapshotOption[]>([]);
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
    if (isOpen) void refreshSources();
  }, [isOpen, refreshSources]);

  async function loadFacts(option: SnapshotOption) {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const data = await getSnapshotFacts(apiBaseUrl, option.userId, option.snapshot, auth);
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

  async function handleFoldIn(mode: FoldInMode) {
    if (!current || !facts) return;
    const ids = selectedFactIds(facts.groups, selected);
    if (ids.length === 0) {
      setError("Select at least one folder or fact to fold in.");
      return;
    }
    if (mode === "replace") {
      const ok = window.confirm(
        "This replaces your current graph with the selected nodes. Continue?",
      );
      if (!ok) return;
    }
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const res = await foldIn(
        apiBaseUrl,
        current.userId,
        current.snapshot,
        ids,
        mode,
        auth,
      );
      setResult(res);
      onFolded?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  const [mountMsg, setMountMsg] = useState<string | null>(null);

  async function handleMount() {
    if (!current) return;
    setBusy(true);
    setError(null);
    setMountMsg(null);
    try {
      await mountSnapshot(
        apiBaseUrl,
        current.snapshot,
        current.isSelf ? undefined : current.userId,
        auth,
      );
      setMountMsg(
        `Mounted "${current.snapshot}" for reads — its facts are now recalled, ` +
          "without being merged into your graph or carried over on save.",
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  const selectedCount = facts ? selectedFactIds(facts.groups, selected).length : 0;

  return (
    <section className={embedded ? "eval-runner eval-runner--embedded" : "eval-runner"}>
      {!embedded && (
        <header className="eval-runner__head">
          <button
            type="button"
            className="eval-runner__collapse"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
          >
            {open ? "▾" : "▸"}{" "}
            <span className="eval-runner__title">Browse snapshots &amp; fold in skills</span>
          </button>
          <span className="eval-runner__hint">
            Pick a teammate&apos;s snapshot, choose folders, and add or replace your own
            graph with them.
          </span>
        </header>
      )}

      {isOpen ? (
        <>
          <div className="eval-runner__row">
            <label className="eval-runner__field">
              <span>Snapshot</span>
              <select
                value={picked}
                onChange={(e) => handlePick(e.target.value)}
                disabled={busy || options.length === 0}
              >
                {options.length === 0 ? (
                  <option value="">No snapshots available</option>
                ) : (
                  <>
                    <option value="">Select a snapshot…</option>
                    {options.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </>
                )}
              </select>
            </label>
            {current ? (
              <button
                type="button"
                className="btn secondary"
                onClick={() => void handleMount()}
                disabled={busy}
                title="Mount this snapshot as a read-only overlay: its facts are included in retrieval reads without being merged into your graph or carried over on save."
              >
                Mount for reads
              </button>
            ) : null}
          </div>
          {mountMsg ? <p className="eval-runner__loaded">{mountMsg}</p> : null}

          {facts && facts.groups.length > 0 ? (
            <div className="eval-runner__browser">
              <ul className="eval-runner__list-folders">
                {facts.groups.map((group) => {
                  const isExpanded = expanded.has(group.key);
                  const checked = groupCheckState(group, selected) === "checked";
                  return (
                    <li
                      key={group.key}
                      className={`eval-runner__entry${checked ? " is-checked" : ""}`}
                    >
                      <div className="eval-runner__entry-row">
                        <GroupCheckbox
                          group={group}
                          selected={selected}
                          onToggle={() => handleToggleGroup(group)}
                        />
                        <button
                          type="button"
                          className="eval-runner__entry-main is-dir"
                          onClick={() => handleExpand(group.key)}
                          aria-expanded={isExpanded}
                          title={isExpanded ? `Hide facts in ${group.label}` : `Show facts in ${group.label}`}
                        >
                          <span className="eval-runner__entry-icon" aria-hidden>
                            📁
                          </span>
                          <span className="eval-runner__entry-name">{group.label}</span>
                          <span className="eval-runner__entry-count">
                            {group.facts.length}
                          </span>
                          <span className="eval-runner__entry-caret">
                            {isExpanded ? "▾" : "›"}
                          </span>
                        </button>
                      </div>
                      {isExpanded ? (
                        <ul className="eval-runner__list-folders fold-in__facts">
                          {group.facts.map((fact) => (
                            <li key={fact.id} className="eval-runner__entry">
                              <label className="eval-runner__entry-row">
                                <input
                                  type="checkbox"
                                  className="eval-runner__entry-check"
                                  checked={selected.has(fact.id)}
                                  onChange={() => handleToggleFact(fact.id)}
                                />
                                <span className="eval-runner__entry-name">{fact.text}</span>
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
            <p className="eval-runner__hint">This snapshot has no facts to fold in.</p>
          ) : null}

          {facts && facts.groups.length > 0 ? (
            <div className="eval-runner__row">
              <div className="eval-runner__actions">
                <button
                  type="button"
                  className="btn primary"
                  onClick={() => void handleFoldIn("add")}
                  disabled={busy || selectedCount === 0}
                  title="Add the selected nodes to your graph"
                >
                  {busy
                    ? "Working…"
                    : `Add to graph (${selectedCount} node${selectedCount === 1 ? "" : "s"})`}
                </button>
                <button
                  type="button"
                  className="btn primary"
                  onClick={() => void handleFoldIn("replace")}
                  disabled={busy || selectedCount === 0}
                  title="Replace your graph with the selected nodes"
                >
                  {busy
                    ? "Working…"
                    : `Replace graph (${selectedCount} node${selectedCount === 1 ? "" : "s"})`}
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
