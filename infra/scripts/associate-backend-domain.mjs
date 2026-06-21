#!/usr/bin/env node
// One-shot: attach mcp.praxiskg.com to the App Runner backend and create the
// Route 53 records App Runner requires.
//
// App Runner custom domains have NO CloudFormation/CDK support, and the record
// values (cert-validation CNAMEs + the DNS target) only exist once the domain
// is associated at runtime — so this can't live in the CDK app. Run it once,
// after the backend is deployed and `mcp` is delegated to Route 53 in Cloudflare.
//
//   node scripts/associate-backend-domain.mjs
//
// Idempotent: re-running re-reads the records and UPSERTs them again.
import { spawnSync } from 'node:child_process';
import { writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import * as path from 'node:path';

const DOMAIN = process.env.MCP_DOMAIN ?? 'mcp.praxiskg.com';
const ZONE_ID = process.env.HOSTED_ZONE_ID ?? 'Z068874626AUKGUC8FK65';
const STACK = 'PraxisBackendServiceStack';
// After writing the records, wait for App Runner to validate the cert and flip the
// domain to ACTIVE, so a green run means "mcp is actually serving". Set
// WAIT_FOR_ACTIVE=0 to skip (e.g. a quick local run); tune the cap with WAIT_TIMEOUT_SEC.
const WAIT_FOR_ACTIVE = process.env.WAIT_FOR_ACTIVE !== '0';
const WAIT_TIMEOUT_SEC = Number(process.env.WAIT_TIMEOUT_SEC ?? 900);

// shell:true on win32 so the `aws` .cmd shim resolves.
// We pass only simple args and parse JSON in JS — no shell-hostile --query
// strings — so cmd.exe quoting is never a problem.
function aws(args) {
  const r = spawnSync('aws', args, {
    shell: process.platform === 'win32',
    encoding: 'utf8',
  });
  return { ok: r.status === 0, out: r.stdout ?? '', err: r.stderr ?? '' };
}

function sleep(seconds) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, seconds * 1000);
}

// 1. Resolve the App Runner service ARN from the deployed stack.
const res = aws(['cloudformation', 'describe-stack-resources', '--stack-name', STACK, '--output', 'json']);
if (!res.ok) { console.error(res.err); process.exit(1); }
const serviceArn = JSON.parse(res.out).StackResources
  .find((r) => r.ResourceType === 'AWS::AppRunner::Service')?.PhysicalResourceId;
if (!serviceArn) { console.error(`No App Runner service found in ${STACK}`); process.exit(1); }
console.log('Service ARN:', serviceArn);

// 1a. Skip if the domain is already ACTIVE on THIS service — nothing to do.
// When the service is recreated it gets a new ARN with no custom domain, so this
// check naturally fails and we re-do the setup. That makes the script safe to run
// on every backend deploy: a no-op normally, self-healing after a replacement.
const existing = aws(['apprunner', 'describe-custom-domains', '--service-arn', serviceArn, '--output', 'json']);
if (existing.ok) {
  const cd = JSON.parse(existing.out).CustomDomains?.find((c) => c.DomainName === DOMAIN);
  if (cd?.Status === 'ACTIVE') {
    console.log(`${DOMAIN} is already ACTIVE on this service — nothing to do.`);
    process.exit(0);
  }
  if (cd) console.log(`${DOMAIN} present with status ${cd.Status} — re-applying records.`);
}

// 2. Associate the domain (ignore "already associated").
const assoc = aws(['apprunner', 'associate-custom-domain',
  '--service-arn', serviceArn, '--domain-name', DOMAIN, '--no-enable-www-subdomain']);
if (!assoc.ok && !/already|exist/i.test(assoc.err)) { console.error(assoc.err); process.exit(1); }
console.log(assoc.ok ? 'Associated.' : 'Already associated — continuing.');

// 3. Poll until App Runner emits the cert-validation records.
let domain, dnsTarget;
process.stdout.write('Waiting for validation records');
for (let i = 0; i < 30; i++) {
  const parsed = JSON.parse(aws(['apprunner', 'describe-custom-domains', '--service-arn', serviceArn, '--output', 'json']).out);
  dnsTarget = parsed.DNSTarget;          // NOTE: top-level on the response, NOT per-domain (and spelled DNSTarget)
  domain = parsed.CustomDomains?.find((c) => c.DomainName === DOMAIN);
  if (domain?.CertificateValidationRecords?.length) break;
  process.stdout.write('.');
  sleep(5);
}
console.log('');
if (!domain?.CertificateValidationRecords?.length) {
  console.error('Validation records did not appear; check the App Runner console.');
  process.exit(1);
}
if (!dnsTarget) { console.error('describe-custom-domains returned no DNSTarget.'); process.exit(1); }

// 4. UPSERT the target CNAME + every validation CNAME into Route 53.
const changes = [
  { Action: 'UPSERT', ResourceRecordSet: { Name: DOMAIN, Type: 'CNAME', TTL: 300, ResourceRecords: [{ Value: dnsTarget }] } },
  ...domain.CertificateValidationRecords.map((r) => ({
    Action: 'UPSERT',
    ResourceRecordSet: { Name: r.Name, Type: r.Type, TTL: 300, ResourceRecords: [{ Value: r.Value }] },
  })),
];
const batchFile = path.join(tmpdir(), 'mcp-r53-batch.json');
writeFileSync(batchFile, JSON.stringify({ Changes: changes }, null, 2));
console.log(`\nApplying ${changes.length} records to zone ${ZONE_ID}:`);
for (const c of changes) console.log(`  ${c.ResourceRecordSet.Name} ${c.ResourceRecordSet.Type} -> ${c.ResourceRecordSet.ResourceRecords[0].Value}`);

const apply = aws(['route53', 'change-resource-record-sets', '--hosted-zone-id', ZONE_ID, '--change-batch', `file://${batchFile}`]);
if (!apply.ok) { console.error(apply.err); process.exit(1); }
console.log('Records written.');

// 5. Wait for App Runner to validate the cert and flip the domain to ACTIVE.
if (!WAIT_FOR_ACTIVE) {
  console.log(`Skipping ACTIVE wait (WAIT_FOR_ACTIVE=0). Check: aws apprunner describe-custom-domains --service-arn ${serviceArn}`);
  process.exit(0);
}
const POLL_SEC = 10;
const maxPolls = Math.max(1, Math.ceil(WAIT_TIMEOUT_SEC / POLL_SEC));
let status = '';
process.stdout.write(`Waiting up to ${WAIT_TIMEOUT_SEC}s for ${DOMAIN} to become ACTIVE`);
for (let i = 0; i < maxPolls; i++) {
  const parsed = JSON.parse(aws(['apprunner', 'describe-custom-domains', '--service-arn', serviceArn, '--output', 'json']).out);
  status = parsed.CustomDomains?.find((c) => c.DomainName === DOMAIN)?.Status ?? 'UNKNOWN';
  if (status === 'ACTIVE') break;
  if (/FAIL/i.test(status)) { console.error(`\n${DOMAIN} entered failure state: ${status}`); process.exit(1); }
  process.stdout.write('.');
  sleep(POLL_SEC);
}
console.log('');
if (status === 'ACTIVE') {
  console.log(`${DOMAIN} is ACTIVE.`);
} else {
  // Soft failure: App Runner often finishes async beyond our cap. continue-on-error
  // in CI keeps the run green; the next deploy's self-check confirms ACTIVE.
  console.error(`${DOMAIN} still ${status} after ${WAIT_TIMEOUT_SEC}s — it usually finishes shortly; ` +
    `re-check or let the next deploy confirm.`);
  process.exit(1);
}
