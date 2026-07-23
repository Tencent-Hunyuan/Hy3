import assert from 'node:assert/strict';
import { readFile, rm } from 'node:fs/promises';
import { resolve } from 'node:path';
import { afterEach, describe, it } from 'node:test';

import { inspectTarget } from '../src/inspector/inspect.js';
import { TargetRegistry } from '../src/target-registry.js';
import { writeTestRegistry } from './helpers/registry.js';

const packageRoot = process.cwd();
const temporaryDirectories: string[] = [];

afterEach(async () => {
  await Promise.all(
    temporaryDirectories.splice(0).map(async (path) => rm(path, { recursive: true })),
  );
});

async function registryFor(
  targets: Parameters<typeof writeTestRegistry>[1],
): Promise<TargetRegistry> {
  const created = await writeTestRegistry(packageRoot, targets);
  temporaryDirectories.push(created.directory);
  return TargetRegistry.load(created.path);
}

describe('inspectTarget', () => {
  it('performs initialize and tools/list against an official SDK fixture', async () => {
    const registry = await registryFor({
      'fixture-good': { fixture: 'good-server' },
    });

    const first = await inspectTarget(registry.get('fixture-good'), {
      target_id: 'fixture-good',
      include_schemas: true,
    });
    const second = await inspectTarget(registry.get('fixture-good'), {
      target_id: 'fixture-good',
      include_schemas: false,
    });

    assert.equal(first.status, 'pass');
    assert.match(first.protocol_version ?? '', /^2025-/);
    assert.deepEqual(first.tools.map((tool) => tool.name), [
      'fixture_echo',
      'fixture_sum',
    ]);
    assert.equal(first.snapshot_hash?.length, 64);
    assert.equal(second.snapshot_hash, first.snapshot_hash);
    assert.deepEqual(second.tools[0]?.input_schema, {});
  });

  it('detects ordinary stdout pollution', async () => {
    const registry = await registryFor({
      polluted: { fixture: 'stdout-pollution' },
    });

    const result = await inspectTarget(registry.get('polluted'), {
      target_id: 'polluted',
      include_schemas: true,
    });

    assert.equal(result.status, 'fail');
    assert.ok(result.findings.some((item) => item.rule_id === 'PROTO-002'));
  });

  it('distinguishes malformed JSON from ordinary log output', async () => {
    const registry = await registryFor({
      malformed: { fixture: 'malformed-stdout' },
    });

    const result = await inspectTarget(registry.get('malformed'), {
      target_id: 'malformed',
      include_schemas: true,
    });

    assert.equal(result.status, 'fail');
    assert.ok(result.findings.some((item) => item.rule_id === 'PROTO-003'));
  });

  it('terminates a target that exceeds its stdout limit', async () => {
    const registry = await registryFor({
      noisy: {
        fixture: 'excess-output',
        limits: { max_stdout_bytes: 1024 },
      },
    });

    const result = await inspectTarget(registry.get('noisy'), {
      target_id: 'noisy',
      include_schemas: true,
    });

    assert.equal(result.status, 'fail');
    assert.ok(result.findings.some((item) => item.rule_id === 'ROBUST-002'));
  });

  it('times out and terminates an unresponsive process', async () => {
    const pidFile = resolve(packageRoot, '.timeout-fixture.pid');
    const registry = await registryFor({
      timeout: {
        fixture: 'timeout-server',
        env: { FIXTURE_PID_FILE: pidFile },
        limits: {
          startup_timeout_ms: 500,
          request_timeout_ms: 500,
          total_timeout_ms: 1500,
        },
      },
    });

    const result = await inspectTarget(registry.get('timeout'), {
      target_id: 'timeout',
      include_schemas: true,
      timeout_ms: 1500,
    });
    const pid = Number(await readFile(pidFile, 'utf8'));
    await rm(pidFile);

    assert.equal(result.status, 'fail');
    assert.ok(result.findings.some((item) => item.rule_id === 'PROTO-004'));
    assert.throws(() => process.kill(pid, 0));
  });

  it('reports a target that exits before initialization', async () => {
    const registry = await registryFor({
      exited: { fixture: 'early-exit' },
    });

    const result = await inspectTarget(registry.get('exited'), {
      target_id: 'exited',
      include_schemas: true,
    });

    assert.equal(result.status, 'fail', JSON.stringify(result, null, 2));
    assert.ok(result.findings.some((item) => item.rule_id === 'ROBUST-004'));
  });

  it('reports a sanitized process startup failure', async () => {
    const unavailableCommand = '/private/synthetic/unavailable-mcp-command';
    const registry = await registryFor({
      unavailable: {
        command: unavailableCommand,
        fixture: 'good-server',
      },
    });

    const result = await inspectTarget(registry.get('unavailable'), {
      target_id: 'unavailable',
      include_schemas: true,
    });

    assert.equal(result.status, 'fail');
    assert.ok(result.findings.some((item) => item.rule_id === 'PROTO-001'));
    assert.equal(JSON.stringify(result).includes(unavailableCommand), false);
  });
});
