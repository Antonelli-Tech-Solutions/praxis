package daemon

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/praxis/session-capture/internal/capture"
	"github.com/praxis/session-capture/internal/diag"
	"github.com/praxis/session-capture/internal/event"
	"github.com/praxis/session-capture/internal/store"
)

// CaptureRuntime is the praxis replacement for the claude+ HQ runtime. It tails
// every hosted session's JSONL transcript under the daemon's config root and
// writes the parsed events to DynamoDB. No WebSocket, no topic gate, no judge —
// just capture -> DynamoDB. The daemon hosts/serves sessions independently; this
// only adds the persistence stream.
type CaptureRuntime struct {
	d      *Daemon
	writer *store.Writer
	stop   chan struct{}
	done   chan struct{}
}

// StartCaptureRuntime builds the DynamoDB writer and starts the transcript
// watcher for the daemon's repo. Table/region come from SESSION_TABLE /
// AWS_REGION (defaults: praxis-sessions, ambient region).
func StartCaptureRuntime(d *Daemon) (*CaptureRuntime, error) {
	table := os.Getenv("SESSION_TABLE")
	if table == "" {
		table = "praxis-sessions"
	}
	w, err := store.New(context.Background(), table, os.Getenv("AWS_REGION"))
	if err != nil {
		return nil, fmt.Errorf("init dynamodb writer: %w", err)
	}
	rt := &CaptureRuntime{
		d:      d,
		writer: w,
		stop:   make(chan struct{}),
		done:   make(chan struct{}),
	}
	go rt.run()
	return rt, nil
}

func (rt *CaptureRuntime) run() {
	defer close(rt.done)
	defer diag.Recover("daemon.captureRuntime")

	repoRoot := rt.d.RepoRoot()
	tailers := map[string]*capture.Tailer{}
	tick := time.NewTicker(500 * time.Millisecond)
	defer tick.Stop()

	emit := func(e event.Event) {
		if err := rt.writer.Put(context.Background(), e); err != nil {
			diag.Logf("capture->dynamodb %s/%s: %v", e.SessionID, e.Kind, err)
		}
	}

	poll := func() {
		// Re-resolve each tick: the daemon's isolated config dir is created lazily
		// on first session spawn, so the projects dir may not exist at start.
		dir, err := capture.ProjectDir(repoRoot)
		if err != nil {
			return
		}
		entries, err := os.ReadDir(dir)
		if err != nil {
			return
		}
		for _, ent := range entries {
			name := ent.Name()
			if ent.IsDir() || !strings.HasSuffix(name, ".jsonl") {
				continue
			}
			sid := strings.TrimSuffix(name, ".jsonl")
			t, ok := tailers[sid]
			if !ok {
				t = capture.NewTailer(sid, filepath.Join(dir, name), emit, nil)
				tailers[sid] = t
			}
			if err := t.Poll(); err != nil {
				diag.Logf("capture poll %s: %v", sid, err)
			}
		}
	}

	for {
		select {
		case <-rt.stop:
			poll() // final drain
			return
		case <-tick.C:
			poll()
		}
	}
}

// Stop halts the watcher after a final drain poll.
func (rt *CaptureRuntime) Stop() {
	select {
	case <-rt.stop:
	default:
		close(rt.stop)
	}
	<-rt.done
}
