import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const recordPath = resolve(packageRoot, 'verification/record.json');
const recordText = await readFile(recordPath, 'utf8');
const record = JSON.parse(recordText);
const sensitivePattern =
  /(?:\/Users\/(?!example(?:\/|$))[^/\s"']+|\/home\/(?!example(?:\/|$))[^/\s"']+|[A-Z]:\\Users\\(?!example(?:\\|$))[^\\\s"']+|sk-[A-Za-z0-9]{12,}|gh[pousr]_[A-Za-z0-9]{20,}|BEGIN [A-Z ]*PRIVATE KEY)/;

assert.equal(record.schema_version, 1);
assert.equal(record.result, 'pass');
assert.match(record.package.sha256, /^[a-f0-9]{64}$/);
assert.equal(record.package.clean_install, 'pass');
assert.equal(record.package.stdio_handshake, 'pass');
assert.equal(record.package.tool_count, 4);
assert.equal(record.package.fixture_call.status, 'pass');

for (const clientName of ['cursor', 'codebuddy']) {
  const client = record.clients[clientName];
  assert.ok(client, `missing ${clientName} verification`);
  assert.match(client.version, /\S/);
  assert.equal(client.configuration_scope, 'project');
  assert.equal(client.fixture_call.status, 'pass');
  assert.equal(client.fixture_call.tool, 'mcpq_inspect_server');
  assert.equal(client.fixture_call.target_id, 'fixture-good');
  assert.match(client.evidence, /^verification\/[a-z]+\.txt$/);
  const evidenceText = await readFile(
    resolve(packageRoot, client.evidence),
    'utf8',
  );
  assert.equal(
    sensitivePattern.test(evidenceText),
    false,
    `${clientName} evidence contains sensitive data`,
  );
  assert.match(evidenceText, /fixture-good/i);
  assert.match(evidenceText, /status:\s*pass/i);
}

assert.equal(record.automated_checks.typecheck, 'pass');
assert.equal(record.automated_checks.lint, 'pass');
assert.equal(record.automated_checks.tests.failed, 0);
assert.equal(record.automated_checks.evaluation.status, 'pass');
assert.equal(record.automated_checks.delivery_verifier, 'pass');
assert.equal(record.automated_checks.offline_demo, 'pass');
assert.equal(record.security_audit.committed_credentials_found, 0);
assert.equal(record.security_audit.committed_personal_paths_found, 0);
assert.equal(record.security_audit.raw_provider_conversations_committed, 0);
assert.equal(record.security_audit.real_target_registries_committed, 0);
assert.equal(sensitivePattern.test(recordText), false);

process.stdout.write(
  `${JSON.stringify(
    {
      status: 'pass',
      package_version: record.package.version,
      cursor_fixture_call: record.clients.cursor.fixture_call.status,
      codebuddy_fixture_call: record.clients.codebuddy.fixture_call.status,
      security_audit: 'pass',
    },
    null,
    2,
  )}\n`,
);
