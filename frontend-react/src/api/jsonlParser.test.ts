import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { parseJsonlFile, parseJsonlFiles } from "./jsonlParser";

const FIXTURE_DIR = join(dirname(fileURLToPath(import.meta.url)), "fixtures");

function loadFixture(name: string): string {
  return readFileSync(join(FIXTURE_DIR, name), "utf-8");
}

describe("jsonlParser", () => {
  it("extracts user and assistant lines from fixture", () => {
    const content = loadFixture("sample-transcript.jsonl");
    const { lines } = parseJsonlFile("sample-transcript.jsonl", content);

    expect(lines.length).toBeGreaterThanOrEqual(3);
    const userLine = lines.find((line) => line.kind === "user_prompt");
    expect(userLine).toBeDefined();
    expect(userLine?.provenance).toBe("logs/sample-transcript.jsonl:2");
    expect(userLine?.text).toContain("pathlib");

    const assistantLine = lines.find((line) => line.kind === "assistant_text");
    expect(assistantLine).toBeDefined();
    expect(assistantLine?.provenance).toBe("logs/sample-transcript.jsonl:3");
  });

  it("skips control rows such as mode", () => {
    const content = loadFixture("sample-transcript.jsonl");
    const { lines } = parseJsonlFile("sample-transcript.jsonl", content);
    expect(lines.some((line) => line.text.includes('"mode"'))).toBe(false);
  });

  it("includes tool_use rows from assistant blocks", () => {
    const content = loadFixture("sample-transcript.jsonl");
    const { lines } = parseJsonlFile("sample-transcript.jsonl", content);
    const toolLine = lines.find((line) => line.kind === "tool_use");
    expect(toolLine).toBeDefined();
    expect(toolLine?.text).toContain("Read");
  });

  it("merges multiple files in parseJsonlFiles", () => {
    const content = loadFixture("sample-transcript.jsonl");
    const session = parseJsonlFiles([
      { name: "a.jsonl", content },
      { name: "b.jsonl", content: '{"type":"user","message":{"role":"user","content":"Short"}}' },
    ]);
    expect(session.files).toHaveLength(2);
    expect(session.lines.length).toBeGreaterThan(3);
    expect(session.source).toBe("local-upload");
  });

  it("warns when file exceeds size cap", () => {
    const huge = "x".repeat(3 * 1024 * 1024);
    const { warnings } = parseJsonlFile("big.jsonl", huge);
    expect(warnings.some((w) => w.includes("2MB"))).toBe(true);
  });
});
