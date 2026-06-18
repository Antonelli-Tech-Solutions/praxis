# session-capture

A wrapper around Claude Code that streams its session messages into a DynamoDB
table — the raw "Claude Code Session Logs" store in the PRAXIS architecture.

## Layout

```
infra/                  (repo root) AWS CDK (TypeScript) — provisions the
                        DynamoDB sessions table (praxis-sessions)
session-capture/wrapper/  Go wrapper (adapted from claude+) — hosts `claude`,
                        tails the JSONL transcript, writes each message to DynamoDB
```

## Provenance

The `wrapper/` capture logic is adapted from the `claude+` wrapper in the
`workflow_harness` project (JSONL transcript tail; CLI only — no GUI/PTY/daemon).
The Command-HQ WebSocket transport is replaced here with a direct DynamoDB
writer. The DynamoDB table design mirrors the `HarnessTable` single-table from
that project's CDK.

## Quick start

```bash
# 1. Deploy the table (CDK lives at the repo root)
cd infra && npm install && npm run deploy

# 2. Build the wrapper
cd ../session-capture/wrapper && go build ./cmd/claude-capture

# 3. Run claude under the wrapper (messages stream to DynamoDB)
SESSION_TABLE=praxis-sessions AWS_REGION=us-east-1 ./claude-capture
```
