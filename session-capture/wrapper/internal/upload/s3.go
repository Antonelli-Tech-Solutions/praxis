// Package upload ships a captured Claude session transcript to S3 as a single
// object — the one durable side effect of the thin `claude-trace` launcher.
//
// The transcript is staged in S3 (not DynamoDB) because a session can exceed
// DynamoDB's 400 KB item limit and because the data is write-once / read-once:
// a remote extractor reads each slice exactly once (triggered by the S3
// ObjectCreated event), writes the derived insights, and the raw slice ages out
// via the bucket's lifecycle rule. The launcher never reads any of this back.
package upload

import (
	"bytes"
	"context"
	"fmt"

	"github.com/aws/aws-sdk-go-v2/aws"
	awsconfig "github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/s3"
)

// Uploader puts session transcript slices into an S3 bucket.
type Uploader struct {
	client *s3.Client
	bucket string
}

// New builds an Uploader using the ambient AWS config (env / shared config /
// instance role). region may be "" to use the environment's default.
func New(ctx context.Context, bucket, region string) (*Uploader, error) {
	var opts []func(*awsconfig.LoadOptions) error
	if region != "" {
		opts = append(opts, awsconfig.WithRegion(region))
	}
	cfg, err := awsconfig.LoadDefaultConfig(ctx, opts...)
	if err != nil {
		return nil, fmt.Errorf("load aws config: %w", err)
	}
	return &Uploader{client: s3.NewFromConfig(cfg), bucket: bucket}, nil
}

// Put writes body to key with the given user metadata. Metadata travels on the
// object (x-amz-meta-*) so the remote extractor can route a slice — by org,
// user, repo, branch, session — without parsing the transcript first.
func (u *Uploader) Put(ctx context.Context, key string, body []byte, metadata map[string]string) error {
	_, err := u.client.PutObject(ctx, &s3.PutObjectInput{
		Bucket:      aws.String(u.bucket),
		Key:         aws.String(key),
		Body:        bytes.NewReader(body),
		ContentType: aws.String("application/x-ndjson"),
		Metadata:    metadata,
	})
	if err != nil {
		return fmt.Errorf("put s3://%s/%s: %w", u.bucket, key, err)
	}
	return nil
}
