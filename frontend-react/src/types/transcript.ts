export type TranscriptLineKind =
  | "user_prompt"
  | "assistant_text"
  | "tool_use"
  | "tool_result"
  | "skipped";

export interface TranscriptLine {
  id: string;
  fileName: string;
  lineNumber: number;
  kind: TranscriptLineKind;
  text: string;
  provenance: string;
  sessionId?: string;
  timestamp?: string;
}

export interface ParsedLogFile {
  name: string;
  lineCount: number;
}

export interface ParsedLogSession {
  files: ParsedLogFile[];
  lines: TranscriptLine[];
  source: "local-upload";
  warnings?: string[];
}

export interface LocalLogFileInput {
  name: string;
  content: string;
}
