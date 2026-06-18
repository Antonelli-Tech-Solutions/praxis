# session-capture

The PRAXIS terminal wrapper around Claude Code — a `claude+`-style per-repo
daemon that hosts the real `claude` CLI over a PTY, multiplexes auto-named
sessions, and streams every session message into a DynamoDB table (the raw
"Claude Code Session Logs" store in the PRAXIS architecture).

Adapted from the `claude+` wrapper in `workflow_harness`, **CLI only** — the
Command-HQ pieces (WebSocket transport, skills/MCP/memory sync, topic gating,
the learning judge) and the desktop GUI are intentionally dropped. The outbound
event stream is replaced with a direct DynamoDB writer.

## Layout

```
infra/                    (repo root) AWS CDK — provisions the praxis-sessions
                          DynamoDB table
session-capture/wrapper/  Go wrapper
  cmd/claude-plus/        the claude+ CLI (host / ls / stop)
  cmd/claude-capture/     minimal non-daemon variant (run claude + capture)
  internal/pty/           PTY host + session multiplexer
  internal/daemon/        per-repo daemon, attach, registry, ls/stop
  internal/capture/       JSONL transcript tailer (+ hooks)
  internal/title/         session auto-naming
  internal/store/         DynamoDB writer
  internal/shell/         terminal chrome (tab bar / status line)
```

## Commands

```
claude+                 attach-or-create the per-repo daemon and host claude
claude+ ls              list running daemons (index, repo, host, sessions, uptime)
claude+ stop=N          stop the daemon at registry index N
claude+ reset           clear all daemon state
claude+ --session=N     attach to the daemon at registry index N
claude+ --version       print version
```

Every hosted session's transcript streams to DynamoDB as it runs.

## Quick start

```bash
# 1. Deploy the table (CDK lives at the repo root)
cd infra && npm install && npm run deploy

# 2. Build the wrapper
cd ../session-capture/wrapper && go build -o claude+ ./cmd/claude-plus

# 3. Host a session (messages stream to DynamoDB)
SESSION_TABLE=praxis-sessions AWS_REGION=us-east-1 ./claude+
```

The DynamoDB writer is optional: if AWS credentials are absent, the daemon
still hosts sessions locally (capture is simply disabled).
