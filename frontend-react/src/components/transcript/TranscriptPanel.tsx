import { useMemo, useState } from "react";
import { postIngestJsonl } from "../../api/apiClient";
import type { Candidate } from "../../types/candidate";
import type { ParsedLogSession, TranscriptLineKind } from "../../types/transcript";

const KIND_OPTIONS: Array<{ value: "all" | TranscriptLineKind; label: string }> = [
  { value: "all", label: "All kinds" },
  { value: "user_prompt", label: "User" },
  { value: "assistant_text", label: "Assistant" },
  { value: "tool_use", label: "Tool use" },
  { value: "tool_result", label: "Tool result" },
];

interface TranscriptPanelProps {
  session: ParsedLogSession;
  candidates: Candidate[];
  apiBaseUrl?: string;
  apiToken?: string;
  rawFiles: Array<{ name: string; content: string }>;
  onSelectCandidate: (candidateId: string) => void;
  onIngestSuccess?: (message: string) => void;
  onIngestError?: (message: string) => void;
}

function kindLabel(kind: TranscriptLineKind): string {
  switch (kind) {
    case "user_prompt":
      return "User";
    case "assistant_text":
      return "Assistant";
    case "tool_use":
      return "Tool";
    case "tool_result":
      return "Result";
    case "skipped":
      return "Skipped";
    default: {
      const neverKind: never = kind;
      return neverKind;
    }
  }
}

export function TranscriptPanel({
  session,
  candidates,
  apiBaseUrl,
  apiToken,
  rawFiles,
  onSelectCandidate,
  onIngestSuccess,
  onIngestError,
}: TranscriptPanelProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [kindFilter, setKindFilter] = useState<"all" | TranscriptLineKind>("all");
  const [ingestPending, setIngestPending] = useState(false);

  const provenanceToCandidateId = useMemo(() => {
    const map = new Map<string, string>();
    for (const candidate of candidates) {
      map.set(candidate.provenance, candidate.id);
    }
    return map;
  }, [candidates]);

  const filteredLines = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    return session.lines.filter((line) => {
      if (kindFilter !== "all" && line.kind !== kindFilter) {
        return false;
      }
      if (!query) {
        return true;
      }
      return (
        line.text.toLowerCase().includes(query) ||
        line.provenance.toLowerCase().includes(query)
      );
    });
  }, [session.lines, searchQuery, kindFilter]);

  async function handleSendToApi() {
    if (!apiBaseUrl) {
      onIngestError?.("Set a live API URL (e.g. Local API preset) before sending logs.");
      return;
    }
    setIngestPending(true);
    try {
      await postIngestJsonl(apiBaseUrl, rawFiles, apiToken);
      onIngestSuccess?.(
        "Logs sent for distillation. Switch to Live API to view pipeline candidates.",
      );
    } catch (error) {
      onIngestError?.(
        error instanceof Error ? error.message : "Failed to send logs to API",
      );
    } finally {
      setIngestPending(false);
    }
  }

  return (
    <section className="transcript-panel" aria-label="Session transcript">
      <div className="transcript-panel__header">
        <button
          type="button"
          className="transcript-panel__toggle"
          onClick={() => setCollapsed((value) => !value)}
          aria-expanded={!collapsed}
        >
          Session transcript ({session.lines.length} lines)
        </button>
        <div className="transcript-panel__actions">
          <button
            type="button"
            className="btn secondary"
            onClick={() => void handleSendToApi()}
            disabled={!apiBaseUrl || ingestPending || rawFiles.length === 0}
            title={
              apiBaseUrl
                ? "POST uploaded JSONL to Matthew's ingest endpoint"
                : "Configure a live API URL to enable distillation"
            }
          >
            {ingestPending ? "Sending…" : "Send to API for distillation"}
          </button>
        </div>
      </div>

      {session.warnings?.length ? (
        <div className="warning-banner transcript-panel__warnings">
          {session.warnings.join(" · ")}
        </div>
      ) : null}

      {!collapsed ? (
        <>
          <div className="transcript-panel__filters">
            <input
              type="search"
              className="transcript-panel__search"
              placeholder="Search transcript…"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              aria-label="Search transcript"
            />
            <select
              className="transcript-panel__kind"
              value={kindFilter}
              onChange={(event) =>
                setKindFilter(event.target.value as "all" | TranscriptLineKind)
              }
              aria-label="Filter by line kind"
            >
              {KIND_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <ul className="transcript-panel__list">
            {filteredLines.map((line) => {
              const candidateId = provenanceToCandidateId.get(line.provenance);
              const isClickable = Boolean(candidateId);
              return (
                <li key={line.id}>
                  <button
                    type="button"
                    className={`transcript-row${isClickable ? " transcript-row--linked" : ""}`}
                    onClick={() => {
                      if (candidateId) {
                        onSelectCandidate(candidateId);
                      }
                    }}
                    disabled={!isClickable}
                    title={
                      isClickable
                        ? "Open matching heuristic candidate"
                        : "No heuristic candidate for this line"
                    }
                  >
                    <span className="transcript-row__meta">
                      <span className="transcript-row__line">L{line.lineNumber}</span>
                      <code className="transcript-row__prov">{line.provenance}</code>
                      <span className={`transcript-row__badge transcript-row__badge--${line.kind}`}>
                        {kindLabel(line.kind)}
                      </span>
                    </span>
                    <span className="transcript-row__text">
                      {line.text.length > 200
                        ? `${line.text.slice(0, 200)}…`
                        : line.text}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
          {filteredLines.length === 0 ? (
            <p className="transcript-panel__empty">No transcript lines match your filters.</p>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
