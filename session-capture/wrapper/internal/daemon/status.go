package daemon

import (
	"github.com/praxis/session-capture/internal/event"
)

// StatusSnapshot is the daemon-wide meter rendered by the status bar: cumulative
// tokens across all sessions, plus the agents/skills drift count maintained by
// the config layer.
type StatusSnapshot struct {
	Tokens int64 `json:"tokens"`
	Drift  int   `json:"drift"`
}

// updateStatus folds an event's token count into the running total. Only the
// message events (user.msg / assistant.msg) carry tokens; every other kind is
// ignored. Called from PublishEvent.
func (d *Daemon) updateStatus(env event.Envelope) {
	switch env.Event.Kind {
	case event.KindUserMsg, event.KindAssistantMsg:
	default:
		return
	}
	if env.Event.Tokens == nil {
		return
	}
	d.statusMu.Lock()
	d.sTokens += *env.Event.Tokens
	d.statusMu.Unlock()
}

// SetDrift records the current agents/skills drift count (config layer, Phase 5).
func (d *Daemon) SetDrift(n int) {
	d.statusMu.Lock()
	d.sDrift = n
	d.statusMu.Unlock()
}

// Status returns the current meter snapshot.
func (d *Daemon) Status() StatusSnapshot {
	d.statusMu.Lock()
	defer d.statusMu.Unlock()
	return StatusSnapshot{Tokens: d.sTokens, Drift: d.sDrift}
}
