module github.com/praxis/session-capture

go 1.25.0

require (
	github.com/aws/aws-sdk-go-v2 v1.42.0
	github.com/aws/aws-sdk-go-v2/config v1.32.25
	github.com/aws/aws-sdk-go-v2/feature/dynamodb/attributevalue v1.20.48
	github.com/aws/aws-sdk-go-v2/service/dynamodb v1.59.0
	github.com/aymanbagabas/go-pty v0.2.3
	github.com/google/uuid v1.6.0
	github.com/hinshun/vt10x v0.0.0-20220301184237-5011da428d02
	github.com/mattn/go-runewidth v0.0.24
)

require (
	github.com/aws/aws-sdk-go-v2/credentials v1.19.24 // indirect
	github.com/aws/aws-sdk-go-v2/feature/ec2/imds v1.18.29 // indirect
	github.com/aws/aws-sdk-go-v2/internal/configsources v1.4.29 // indirect
	github.com/aws/aws-sdk-go-v2/internal/endpoints/v2 v2.7.29 // indirect
	github.com/aws/aws-sdk-go-v2/internal/v4a v1.4.30 // indirect
	github.com/aws/aws-sdk-go-v2/service/dynamodbstreams v1.34.0 // indirect
	github.com/aws/aws-sdk-go-v2/service/internal/accept-encoding v1.13.12 // indirect
	github.com/aws/aws-sdk-go-v2/service/internal/endpoint-discovery v1.12.6 // indirect
	github.com/aws/aws-sdk-go-v2/service/internal/presigned-url v1.13.29 // indirect
	github.com/aws/aws-sdk-go-v2/service/signin v1.2.0 // indirect
	github.com/aws/aws-sdk-go-v2/service/sso v1.31.3 // indirect
	github.com/aws/aws-sdk-go-v2/service/ssooidc v1.36.6 // indirect
	github.com/aws/aws-sdk-go-v2/service/sts v1.43.3 // indirect
	github.com/aws/smithy-go v1.27.1 // indirect
	github.com/clipperhouse/uax29/v2 v2.2.0 // indirect
	github.com/creack/pty v1.1.24 // indirect
	github.com/u-root/u-root v0.16.0 // indirect
	golang.org/x/crypto v0.51.0 // indirect
	golang.org/x/sys v0.46.0 // indirect
	golang.org/x/term v0.44.0 // indirect
)

replace github.com/hinshun/vt10x => ./third_party/vt10x
