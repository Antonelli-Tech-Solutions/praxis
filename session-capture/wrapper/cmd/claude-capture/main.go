// Command claude-capture is a thin CLI wrapper around Claude Code that streams
// each session's JSONL transcript into the praxis-sessions DynamoDB table.
//
// It launches the real `claude` CLI (passing through all args, inheriting
// stdio) and, while it runs, watches ~/.claude/projects/<hash>/ for session
// transcripts, tailing every .jsonl and writing the parsed events to DynamoDB.
//
// No PTY, no GUI, no daemon — just the capture path plus a direct DynamoDB
// writer.
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
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/praxis/session-capture/internal/capture"
	"github.com/praxis/session-capture/internal/event"
	"github.com/praxis/session-capture/internal/store"
)

func main() {
	if err := run(); err != nil {
		log.Fatalf("claude-capture: %v", err)
	}
}

func run() error {
	table := flag.String("table", envOr("SESSION_TABLE", "praxis-sessions"), "DynamoDB table name")
	region := flag.String("region", os.Getenv("AWS_REGION"), "AWS region (defaults to ambient config)")
	interval := flag.Duration("interval", 500*time.Millisecond, "transcript poll interval")
	flag.Parse()

	repoRoot, err := os.Getwd()
	if err != nil {
		return fmt.Errorf("getwd: %w", err)
	}
	projectDir, err := capture.ProjectDir(repoRoot)
	if err != nil {
		return fmt.Errorf("resolve project dir: %w", err)
	}

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt)
	defer stop()

	writer, err := store.New(ctx, *table, *region)
	if err != nil {
		return fmt.Errorf("init dynamodb writer: %w", err)
	}

	emit := func(e event.Event) {
		if err := writer.Put(ctx, e); err != nil {
			fmt.Fprintf(os.Stderr, "claude-capture: write %s/%s: %v\n", e.SessionID, e.Kind, err)
		}
	}

	log.Printf("claude-capture: table=%s region=%s watching %s", *table, regionLabel(*region), projectDir)

	// Watch transcripts in the background while claude runs.
	var wg sync.WaitGroup
	wg.Add(1)
	watchDone := make(chan struct{})
	go func() {
		defer wg.Done()
		watch(ctx, projectDir, *interval, emit, watchDone)
	}()

	// Launch the real claude CLI, passing through args and inheriting stdio.
	code, err := runClaude(ctx, flag.Args())

	// Let the watcher drain one last poll, then stop it.
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

// watch polls projectDir for *.jsonl transcripts, maintaining one Tailer per
// session and emitting parsed events until ctx is done or stopDrain is closed
// (after which it does one final poll so the last turns are not lost).
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
				fmt.Fprintf(os.Stderr, "claude-capture: poll %s: %v\n", sid, err)
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
