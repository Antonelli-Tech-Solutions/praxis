// Package store writes captured session events to the praxis-sessions DynamoDB
// table. It replaces the claude+ Command-HQ WebSocket transport with a direct
// PutItem writer.
package store

import (
	"context"
	"encoding/json"
	"fmt"
	"sync"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	awsconfig "github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/feature/dynamodb/attributevalue"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb"

	"github.com/praxis/session-capture/internal/event"
)

// item is one DynamoDB row. Single-table layout (mirrors the CDK stack):
//
//	PK = SESSION#<sessionId>   SK = MSG#<zero-padded-seq>
//	GSI1PK = PROJECT#<projectId>  GSI1SK = TS#<capturedAt>   (when projectId known)
type item struct {
	PK          string `dynamodbav:"PK"`
	SK          string `dynamodbav:"SK"`
	GSI1PK      string `dynamodbav:"GSI1PK,omitempty"`
	GSI1SK      string `dynamodbav:"GSI1SK,omitempty"`
	Kind        string `dynamodbav:"kind"`
	SessionID   string `dynamodbav:"sessionId"`
	ProjectID   string `dynamodbav:"projectId,omitempty"`
	Tool        string `dynamodbav:"tool,omitempty"`
	ArgsSummary string `dynamodbav:"argsSummary,omitempty"`
	Text        string `dynamodbav:"text,omitempty"`
	Summary     string `dynamodbav:"summary,omitempty"`
	Tokens      int64  `dynamodbav:"tokens,omitempty"`
	OK          *bool  `dynamodbav:"ok,omitempty"`
	CapturedAt  string `dynamodbav:"capturedAt"`
	Raw         string `dynamodbav:"raw"`
}

// Writer puts session events into a DynamoDB table.
type Writer struct {
	client *dynamodb.Client
	table  string

	mu  sync.Mutex
	seq map[string]int64 // per-session monotonic sequence for the SK
}

// New builds a Writer using the ambient AWS config (env / shared config /
// instance role). region may be "" to use the environment's default.
func New(ctx context.Context, table, region string) (*Writer, error) {
	var opts []func(*awsconfig.LoadOptions) error
	if region != "" {
		opts = append(opts, awsconfig.WithRegion(region))
	}
	cfg, err := awsconfig.LoadDefaultConfig(ctx, opts...)
	if err != nil {
		return nil, fmt.Errorf("load aws config: %w", err)
	}
	return &Writer{
		client: dynamodb.NewFromConfig(cfg),
		table:  table,
		seq:    make(map[string]int64),
	}, nil
}

// next returns the next monotonic sequence for a session.
func (w *Writer) next(sessID string) int64 {
	w.mu.Lock()
	defer w.mu.Unlock()
	n := w.seq[sessID] + 1
	w.seq[sessID] = n
	return n
}

// Put writes a single captured event as a table item.
func (w *Writer) Put(ctx context.Context, e event.Event) error {
	seq := w.next(e.SessionID)
	now := time.Now().UTC().Format(time.RFC3339Nano)

	raw, err := json.Marshal(e)
	if err != nil {
		return fmt.Errorf("marshal event: %w", err)
	}

	it := item{
		PK:          "SESSION#" + e.SessionID,
		SK:          fmt.Sprintf("MSG#%020d", seq),
		Kind:        string(e.Kind),
		SessionID:   e.SessionID,
		ProjectID:   e.ProjectID,
		Tool:        e.Tool,
		ArgsSummary: e.ArgsSummary,
		Text:        e.Text,
		Summary:     e.Summary,
		OK:          e.OK,
		CapturedAt:  now,
		Raw:         string(raw),
	}
	if e.Tokens != nil {
		it.Tokens = *e.Tokens
	}
	if e.ProjectID != "" {
		it.GSI1PK = "PROJECT#" + e.ProjectID
		it.GSI1SK = "TS#" + now
	}

	av, err := attributevalue.MarshalMap(it)
	if err != nil {
		return fmt.Errorf("marshal item: %w", err)
	}
	_, err = w.client.PutItem(ctx, &dynamodb.PutItemInput{
		TableName: aws.String(w.table),
		Item:      av,
	})
	if err != nil {
		return fmt.Errorf("put item: %w", err)
	}
	return nil
}
