import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { distillCandidatesFromTranscript } from "./heuristicDistiller";
import { parseJsonlFile } from "./jsonlParser";

const FIXTURE = join(
  dirname(fileURLToPath(import.meta.url)),
  "fixtures",
  "sample-transcript.jsonl",
);

describe("heuristicDistiller", () => {
  const lines = parseJsonlFile(
    "sample-transcript.jsonl",
    readFileSync(FIXTURE, "utf-8"),
  ).lines;

  it("creates proposed candidates from long user prompts", () => {
    const candidates = distillCandidatesFromTranscript(lines);
    const promptCandidate = candidates.find((c) =>
      c.provenance === "logs/sample-transcript.jsonl:2",
    );
    expect(promptCandidate).toBeDefined();
    expect(promptCandidate?.state).toBe("proposed");
    expect(promptCandidate?.id).toMatch(/^local_/);
    expect(promptCandidate?.confidence).toBeGreaterThanOrEqual(0.55);
  });

  it("boosts assistant candidate after user correction", () => {
    const candidates = distillCandidatesFromTranscript(lines);
    const assistantCandidate = candidates.find((c) =>
      c.provenance === "logs/sample-transcript.jsonl:3",
    );
    expect(assistantCandidate).toBeDefined();
    expect(assistantCandidate?.category).toBe("error_fix");
    expect(assistantCandidate?.confidence).toBe(0.75);
  });

  it("uses logs provenance format", () => {
    const candidates = distillCandidatesFromTranscript(lines);
    for (const candidate of candidates) {
      expect(candidate.provenance).toMatch(/^logs\/.+:\d+$/);
    }
  });
});
