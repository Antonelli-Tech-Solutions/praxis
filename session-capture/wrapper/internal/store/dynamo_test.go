package store

import (
	"context"
	"fmt"
	"os"
	"testing"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb"
	ddbtypes "github.com/aws/aws-sdk-go-v2/service/dynamodb/types"

	"github.com/praxis/session-capture/internal/event"
)

// next() must be monotonic and per-session (pure, no AWS).
func TestNextSequencePerSession(t *testing.T) {
	w := &Writer{seq: make(map[string]int64)}
	if got := w.next("a"); got != 1 {
		t.Fatalf("first a = %d, want 1", got)
	}
	if got := w.next("a"); got != 2 {
		t.Fatalf("second a = %d, want 2", got)
	}
	if got := w.next("b"); got != 1 {
		t.Fatalf("first b = %d, want 1", got)
	}
}

// Integration: round-trips a real event through the deployed table. Skipped
// unless SESSION_TABLE is set (e.g. SESSION_TABLE=praxis-sessions go test ...).
func TestIntegrationPutRoundTrip(t *testing.T) {
	table := os.Getenv("SESSION_TABLE")
	if table == "" {
		t.Skip("set SESSION_TABLE to run the DynamoDB integration test")
	}
	ctx := context.Background()
	w, err := New(ctx, table, os.Getenv("AWS_REGION"))
	if err != nil {
		t.Fatalf("New: %v", err)
	}

	sid := "integ-" + time.Now().UTC().Format("20060102T150405.000000")
	const text = "hello from the integration test"
	tok := int64(7)
	e := event.Event{
		Kind:      event.KindUserMsg,
		SessionID: sid,
		ProjectID: "praxis-test",
		Text:      text,
		Tokens:    &tok,
	}
	if err := w.Put(ctx, e); err != nil {
		t.Fatalf("Put: %v", err)
	}

	key := map[string]ddbtypes.AttributeValue{
		"PK": &ddbtypes.AttributeValueMemberS{Value: "SESSION#" + sid},
		"SK": &ddbtypes.AttributeValueMemberS{Value: fmt.Sprintf("MSG#%020d", 1)},
	}
	out, err := w.client.GetItem(ctx, &dynamodb.GetItemInput{
		TableName: aws.String(table),
		Key:       key,
	})
	if err != nil {
		t.Fatalf("GetItem: %v", err)
	}
	if out.Item == nil {
		t.Fatal("item not found after Put")
	}
	got, ok := out.Item["text"].(*ddbtypes.AttributeValueMemberS)
	if !ok || got.Value != text {
		t.Fatalf("text = %v, want %q", out.Item["text"], text)
	}

	// Cleanup so the test table doesn't accumulate fixtures.
	if _, err := w.client.DeleteItem(ctx, &dynamodb.DeleteItemInput{
		TableName: aws.String(table),
		Key:       key,
	}); err != nil {
		t.Logf("cleanup DeleteItem: %v", err)
	}
}
