import * as cdk from 'aws-cdk-lib/core';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import { Construct } from 'constructs';

/**
 * Shared network for the PRAXIS stack: one cheap VPC for the VPC-bound
 * workloads. Today the Phoenix EC2 instance lives here; new VPC-bound stacks
 * should consume this rather than minting their own.
 *
 * The knowledge-graph RDS instance deliberately does NOT use this VPC — it is
 * already deployed with live tenant data, and an instance can't change VPC
 * without a destructive replacement, so it keeps its own VPC (see
 * KnowledgeGraphDbStack). Greenfield stacks have no such constraint.
 *
 * Public subnets only, no NAT gateways: every workload here is reached directly
 * over its own security group (Phoenix behind an Elastic IP), so NAT would add
 * cost for no benefit.
 */
export class NetworkStack extends cdk.Stack {
  public readonly vpc: ec2.Vpc;

  constructor(scope: Construct, id: string, props: cdk.StackProps = {}) {
    super(scope, id, props);

    this.vpc = new ec2.Vpc(this, 'PraxisVpc', {
      maxAzs: 2,
      natGateways: 0,
      subnetConfiguration: [
        { name: 'public', subnetType: ec2.SubnetType.PUBLIC, cidrMask: 24 },
      ],
    });

    new cdk.CfnOutput(this, 'VpcId', { value: this.vpc.vpcId });
  }
}
