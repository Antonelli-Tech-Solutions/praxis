# praxis-session-capture

A wrapper around Claude Code that streams its session messages into a DynamoDB
table — the raw "Claude Code Session Logs" store in the PRAXIS architecture.

This is a standalone repo, consumed by the [`praxis`](../) project as a git
submodule.

## Layout

```
infra/      AWS CDK (TypeScript) — provisions the DynamoDB sessions table
wrapper/    Go wrapper (adapted from claude+) — hosts `claude`, tails the
            JSONL transcript, and writes each message to DynamoDB
```

## Provenance

The `wrapper/` capture logic is adapted from the `claude+` wrapper in the
`workflow_harness` project (PTY host + JSONL transcript tail). The Command-HQ
WebSocket transport is replaced here with a direct DynamoDB writer. The DynamoDB
table design mirrors the `HarnessTable` single-table from that project's CDK.

## Quick start

```bash
# 1. Deploy the table
cd infra && npm install && npm run deploy

# 2. Build the wrapper
cd ../wrapper && go build ./cmd/claude-capture

# 3. Run claude under the wrapper (messages stream to DynamoDB)
SESSION_TABLE=praxis-sessions AWS_REGION=us-east-1 ./claude-capture
```
