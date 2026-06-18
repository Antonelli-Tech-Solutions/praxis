import * as cdk from 'aws-cdk-lib/core';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import { Construct } from 'constructs';

export interface SessionsTableStackProps extends cdk.StackProps {
  /** Physical DynamoDB table name. Defaults to `praxis-sessions`. */
  readonly tableName?: string;
}

/**
 * The raw "Claude Code Session Logs" store for PRAXIS.
 *
 * A single-table design (mirroring the claude+ `HarnessTable`) so a session and
 * all of its messages live under one partition and read back in order:
 *
 *   PK = SESSION#<sessionId>     SK = MSG#<zero-padded-seq>   — one item per message
 *   PK = SESSION#<sessionId>     SK = META                    — session metadata
 *
 * GSI1 lets us list sessions by project / recency without a scan:
 *   GSI1PK = PROJECT#<projectId> GSI1SK = TS#<iso8601>
 *
 * PAY_PER_REQUEST (spiky, user-driven writes), streams on (downstream learning
 * pipeline taps NEW_AND_OLD_IMAGES), PITR on, and a `ttl` attribute so raw logs
 * can be aged out automatically if a retention window is set per item.
 */
export class SessionsTableStack extends cdk.Stack {
  public readonly table: dynamodb.Table;

  constructor(scope: Construct, id: string, props: SessionsTableStackProps = {}) {
    super(scope, id, props);

    this.table = new dynamodb.Table(this, 'SessionsTable', {
      tableName: props.tableName ?? 'praxis-sessions',
      partitionKey: { name: 'PK', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'SK', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      stream: dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
      pointInTimeRecoverySpecification: { pointInTimeRecoveryEnabled: true },
      timeToLiveAttribute: 'ttl',
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    this.table.addGlobalSecondaryIndex({
      indexName: 'GSI1',
      partitionKey: { name: 'GSI1PK', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'GSI1SK', type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    new cdk.CfnOutput(this, 'TableName', { value: this.table.tableName });
    new cdk.CfnOutput(this, 'TableArn', { value: this.table.tableArn });
    new cdk.CfnOutput(this, 'TableStreamArn', {
      value: this.table.tableStreamArn ?? 'none',
    });
  }
}
