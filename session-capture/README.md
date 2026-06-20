# session-capture

A thin, **opt-in** wrapper around Claude Code. Run `claude-trace` instead of
`claude` and, when your work ships as a PR, that session's transcript is uploaded
to S3 for a remote extractor to mine for insights. Running plain `claude`
captures nothing.

This replaces the old `claude+` daemon (PTY host, session multiplexer, terminal
chrome, per-message DynamoDB writes). None of that is needed to capture a
session: Claude Code already writes a full JSONL transcript to disk, so the
launcher just watches it.

## How it works

1. `claude-trace` execs the real `claude`, passing through all args and
   inheriting stdio — the terminal experience is identical to plain `claude`.
2. While the session runs, it tails the transcript JSONL Claude writes under
   `~/.claude/projects/<hash>/<sessionId>.jsonl`, watching for one signal: a
   `git push` / `gh pr create`.
3. On that signal it uploads the session transcript to S3 as a single object,
   keyed by `org / user / repo / branch / sessionId` and tagged with the same
   values as object metadata.

The data is **write-once / read-once**: a remote extractor (triggered by the S3
`ObjectCreated` event via EventBridge) reads each slice exactly once, writes the
derived insights to the `praxis-session-insights` table, and the raw slice ages
out via the bucket lifecycle rule. The launcher never reads any of it back — so
there is no large "session logs" table to query or scan.

## Layout

```
session-capture/wrapper/       Go launcher
  cmd/claude-capture/          the `claude-trace` binary (claude passthrough)
  internal/capture/            JSONL transcript tailer + parser
  internal/upload/             S3 uploader
  internal/event/              shared event envelope (tailer output type)
  internal/config/             repo / owner-repo resolution
```

## Configuration

| Env var               | Purpose                                          | Default            |
| --------------------- | ------------------------------------------------ | ------------------ |
| `PRAXIS_SLICE_BUCKET` | S3 bucket for slices; **unset disables capture** | —                  |
| `PRAXIS_ORG_ID`       | tenant org id (S3 key prefix + metadata)         | `default`          |
| `PRAXIS_USER_ID`      | tenant user id                                   | OS user            |
| `AWS_REGION`          | region for the S3 client                         | ambient AWS config |

Capture is best-effort: with no bucket configured or no AWS credentials, the
session still runs normally — it just isn't captured. `claude-trace` never makes
a session worse than plain `claude`.

The S3 slices bucket (with lifecycle expiry + EventBridge notifications) and the
`praxis-session-insights` table are provisioned by the `infra/` CDK app in a
separate change.

## Quick start

```bash
# Build the launcher
cd session-capture/wrapper && go build -o claude-trace ./cmd/claude-capture

# Run an opt-in session (uploads to S3 on git push / gh pr create)
PRAXIS_SLICE_BUCKET=praxis-session-slices AWS_REGION=us-east-1 ./claude-trace
```
