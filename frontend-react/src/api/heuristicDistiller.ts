import type { RawCandidate } from "../types/candidate";
import type { TranscriptLine } from "../types/transcript";

const CORRECTION_RE = /\b(no|wrong|instead|don't|do not)\b/i;
const SLASH_COMMAND_RE = /^\/[a-z0-9_-]+(\s|$)/i;

function sanitizeIdPart(value: string): string {
  return value.replace(/[^a-zA-Z0-9_]+/g, "_").slice(0, 40);
}

function titleFromText(text: string): string {
  const first = text.trim().split("\n", 1)[0];
  const sentence = first.split(/[.!?]\s/, 1)[0].trim();
  return (sentence || first).slice(0, 120);
}

function isSlashOnlyPrompt(text: string): boolean {
  const trimmed = text.trim();
  if (!SLASH_COMMAND_RE.test(trimmed)) {
    return false;
  }
  const withoutCommand = trimmed.replace(SLASH_COMMAND_RE, "").trim();
  return withoutCommand.length < 20;
}

function baseCandidate(
  line: TranscriptLine,
  content: string,
  confidence: number,
  category?: string,
): RawCandidate {
  const id = `local_${sanitizeIdPart(line.fileName)}_${line.lineNumber}`;
  return {
    id,
    title: titleFromText(content),
    content,
    state: "proposed",
    confidence,
    provenance: line.provenance,
    createdAt: line.timestamp ?? new Date().toISOString(),
    category,
    auditTrail: [
      {
        action: "heuristic_distilled",
        timestamp: new Date().toISOString(),
        provenance: line.provenance,
        actor: "browser-preview",
      },
    ],
  };
}

export function distillCandidatesFromTranscript(
  lines: TranscriptLine[],
): RawCandidate[] {
  const candidates: RawCandidate[] = [];
  const candidateByProvenance = new Map<string, RawCandidate>();

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];

    if (line.kind === "user_prompt") {
      const text = line.text.trim();
      if (text.length < 40 || isSlashOnlyPrompt(text)) {
        continue;
      }
      const candidate = baseCandidate(line, text, 0.65, "pattern");
      candidates.push(candidate);
      candidateByProvenance.set(line.provenance, candidate);
      continue;
    }

    if (line.kind === "assistant_text") {
      const text = line.text.trim();
      if (text.length < 80) {
        continue;
      }
      const candidate = baseCandidate(line, text, 0.58, "pattern");
      candidates.push(candidate);
      candidateByProvenance.set(line.provenance, candidate);

      const next = lines[index + 1];
      if (next?.kind === "user_prompt" && CORRECTION_RE.test(next.text)) {
        candidate.confidence = 0.75;
        candidate.category = "error_fix";
      }
    }
  }

  return candidates;
}
