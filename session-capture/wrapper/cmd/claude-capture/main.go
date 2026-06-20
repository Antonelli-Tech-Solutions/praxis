// Command claude-trace is a thin opt-in wrapper around Claude Code. A user who
// wants their session captured runs `claude-trace` instead of `claude`; running
// plain `claude` captures nothing. The launcher:
//
//   - execs the real `claude` CLI, passing through all args and inheriting stdio,
//     so the terminal experience is identical to running claude directly; and
//   - tails the session transcript JSONL Claude writes under ~/.claude, watching
//     only for a `git push` / `gh pr create`. On that signal it uploads the
//     session's transcript to S3 as one object, tagged with org/user/repo/branch/
//     session metadata.
//
// That is the whole job. The raw slice is read once by a remote extractor
// (triggered by the S3 ObjectCreated event), which derives insights and lets the
// slice age out via the bucket lifecycle rule — the launcher never reads it back.
//
// No PTY, no daemon, no per-message database writes.
package main

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"log"
	"os"
	"os/exec"
	"os/signal"
	"os/user"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/praxis/session-capture/internal/capture"
	"github.com/praxis/session-capture/internal/config"
	"github.com/praxis/session-capture/internal/event"
	"github.com/praxis/session-capture/internal/upload"
)

func main() {
	if err := run(); err != nil {
		log.Fatalf("claude-trace: %v", err)
	}
}

func run() error {
	bucket := flag.String("bucket", os.Getenv("PRAXIS_SLICE_BUCKET"), "S3 bucket for session transcript slices")
	region := flag.String("region", os.Getenv("AWS_REGION"), "AWS region (defaults to ambient config)")
	interval := flag.Duration("interval", 500*time.Millisecond, "transcript poll interval")
	flag.Parse()

	cwd, err := os.Getwd()
	if err != nil {
		return fmt.Errorf("getwd: %w", err)
	}
	repoRoot := config.RepoRootFor(cwd)
	repo := config.RepoNameFor(repoRoot)
	org := envOr("PRAXIS_ORG_ID", "default")
	usr := envOr("PRAXIS_USER_ID", osUser())

	projectDir, err := capture.ProjectDir(repoRoot)
	if err != nil {
		return fmt.Errorf("resolve project dir: %w", err)
	}

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt)
	defer stop()

	// Capture is opt-in AND best-effort: with no bucket configured (or no AWS
	// creds) we still host the session, we just don't upload. claude-trace must
	// never make the session worse than plain claude.
	var sink *uploadSink
	if *bucket == "" {
		log.Printf("claude-trace: no S3 bucket configured (PRAXIS_SLICE_BUCKET); capture disabled")
	} else {
		u, err := upload.New(ctx, *bucket, *region)
		if err != nil {
			log.Printf("claude-trace: S3 init failed, capture disabled: %v", err)
		} else {
			sink = &uploadSink{
				ctx: ctx, up: u, projectDir: projectDir,
				repoRoot: repoRoot, repo: repo, org: org, user: usr,
			}
			log.Printf("claude-trace: bucket=%s region=%s repo=%s org=%s user=%s",
				*bucket, regionLabel(*region), repo, org, usr)
		}
	}

	// Watch transcripts in the background while claude runs, looking only for the
	// push/PR signal. Skipped entirely when capture is disabled.
	var wg sync.WaitGroup
	watchDone := make(chan struct{})
	if sink != nil {
		wg.Add(1)
		go func() {
			defer wg.Done()
			watch(ctx, projectDir, *interval, sink.onEvent, watchDone)
		}()
	}

	code, err := runClaude(ctx, flag.Args())

	close(watchDone)
	wg.Wait()

	if err != nil {
		return err
	}
	if code != 0 {
		os.Exit(code)
	}
	return nil
}

// uploadSink holds the context the push handler needs to build an S3 object for
// the session that ran the push.
type uploadSink struct {
	ctx        context.Context
	up         *upload.Uploader
	projectDir string
	repoRoot   string
	repo       string // owner/repo display name
	org        string
	user       string
}

// onEvent is the EventSink: it ignores everything except a Bash tool call that
// is a git push / gh pr create, on which it uploads the originating session's
// transcript slice. Called from the single watch goroutine, so it is serial.
func (s *uploadSink) onEvent(e event.Event) {
	if e.Kind != event.KindToolCall || !isPushCommand(e.Tool, e.ArgsSummary) {
		return
	}
	branch := gitBranch(s.repoRoot)
	path := filepath.Join(s.projectDir, e.SessionID+".jsonl")
	body, err := os.ReadFile(path)
	if err != nil {
		fmt.Fprintf(os.Stderr, "claude-trace: read transcript %s: %v\n", e.SessionID, err)
		return
	}
	key := sliceKey(s.org, s.user, s.repo, branch, e.SessionID)
	meta := map[string]string{
		"org": s.org, "user": s.user, "repo": s.repo,
		"branch": branch, "session-id": e.SessionID,
	}
	if err := s.up.Put(s.ctx, key, body, meta); err != nil {
		fmt.Fprintf(os.Stderr, "claude-trace: upload %s: %v\n", e.SessionID, err)
		return
	}
	log.Printf("claude-trace: uploaded slice repo=%s branch=%s session=%s (%d bytes)",
		s.repo, branch, e.SessionID, len(body))
}

// isPushCommand reports whether a tool call is a git push or gh pr create — the
// signal that a PR's worth of work just shipped and is worth capturing.
func isPushCommand(tool, args string) bool {
	if tool != "Bash" {
		return false
	}
	a := strings.ToLower(args)
	return strings.Contains(a, "git push") || strings.Contains(a, "gh pr create")
}

// watch polls projectDir for *.jsonl transcripts, maintaining one Tailer per
// session and feeding parsed events to emit until ctx is done or stopDrain is
// closed (after which it does one final poll so a push on the last turn is not
// lost).
func watch(ctx context.Context, projectDir string, every time.Duration, emit capture.EventSink, stopDrain <-chan struct{}) {
	tailers := map[string]*capture.Tailer{}
	tick := time.NewTicker(every)
	defer tick.Stop()

	poll := func() {
		entries, err := os.ReadDir(projectDir)
		if err != nil {
			return // dir may not exist until the first session starts
		}
		for _, ent := range entries {
			name := ent.Name()
			if ent.IsDir() || !strings.HasSuffix(name, ".jsonl") {
				continue
			}
			sid := strings.TrimSuffix(name, ".jsonl")
			t, ok := tailers[sid]
			if !ok {
				t = capture.NewTailer(sid, filepath.Join(projectDir, name), emit, nil)
				tailers[sid] = t
			}
			if err := t.Poll(); err != nil {
				fmt.Fprintf(os.Stderr, "claude-trace: poll %s: %v\n", sid, err)
			}
		}
	}

	for {
		select {
		case <-ctx.Done():
			return
		case <-stopDrain:
			poll() // final drain
			return
		case <-tick.C:
			poll()
		}
	}
}

// runClaude execs the real claude CLI with the given args, inheriting stdio.
// Returns its exit code.
func runClaude(ctx context.Context, args []string) (int, error) {
	bin, err := exec.LookPath("claude")
	if err != nil {
		return 1, fmt.Errorf("`claude` not found on PATH: %w", err)
	}
	cmd := exec.CommandContext(ctx, bin, args...)
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		var exit *exec.ExitError
		if errors.As(err, &exit) {
			return exit.ExitCode(), nil
		}
		return 1, fmt.Errorf("run claude: %w", err)
	}
	return 0, nil
}

// gitBranch returns repoRoot's current branch, or "detached" when it cannot be
// resolved (no git / detached HEAD). Best-effort: a missing branch never blocks
// an upload.
func gitBranch(repoRoot string) string {
	out, err := exec.Command("git", "-C", repoRoot, "rev-parse", "--abbrev-ref", "HEAD").Output()
	if err != nil {
		return "detached"
	}
	b := strings.TrimSpace(string(out))
	if b == "" || b == "HEAD" {
		return "detached"
	}
	return b
}

// sliceKey builds the S3 object key. The org/user prefix mirrors the tenancy
// model; the branch in the key (last path segment before the file) makes a
// re-push of the SAME branch overwrite its prior slice (last push wins), while
// distinct branches in one session produce distinct objects.
func sliceKey(org, user, repo, branch, sessionID string) string {
	return strings.Join([]string{
		"slices",
		"org=" + slug(org),
		"user=" + slug(user),
		"repo=" + slug(repo),
		"branch=" + slug(branch),
		sessionID + ".jsonl",
	}, "/")
}

// slug maps anything outside [a-z0-9.-] to a dash so a value is safe in an S3
// key path segment (owner/repo and feat/x branch names contain slashes).
func slug(s string) string {
	s = strings.ToLower(strings.TrimSpace(s))
	var b strings.Builder
	prevDash := false
	for _, r := range s {
		if (r >= 'a' && r <= 'z') || (r >= '0' && r <= '9') || r == '.' {
			b.WriteRune(r)
			prevDash = false
		} else if !prevDash {
			b.WriteByte('-')
			prevDash = true
		}
	}
	out := strings.Trim(b.String(), "-")
	if out == "" {
		return "unknown"
	}
	return out
}

func osUser() string {
	if u, err := user.Current(); err == nil && u.Username != "" {
		// Strip a Windows DOMAIN\user prefix.
		if i := strings.LastIndexAny(u.Username, `\/`); i >= 0 {
			return u.Username[i+1:]
		}
		return u.Username
	}
	return "unknown"
}

func envOr(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}

func regionLabel(r string) string {
	if r == "" {
		return "(ambient)"
	}
	return r
}
