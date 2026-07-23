import assert from 'node:assert/strict';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterEach, describe, it } from 'node:test';

import { TargetRegistry } from '../src/target-registry.js';

const temporaryDirectories: string[] = [];

afterEach(async () => {
  await Promise.all(
    temporaryDirectories.splice(0).map(async (path) => rm(path, { recursive: true })),
  );
});

async function registryWith(target: Record<string, unknown>): Promise<string> {
  const directory = await mkdtemp(join(tmpdir(), 'hy3-mcpq-registry-'));
  temporaryDirectories.push(directory);
  const path = join(directory, 'targets.json');
  await writeFile(
    path,
    JSON.stringify({
      version: 1,
      allowed_roots: [directory],
      defaults: {
        startup_timeout_ms: 1000,
        request_timeout_ms: 1000,
        total_timeout_ms: 3000,
        max_stdout_bytes: 65536,
        max_stderr_bytes: 65536,
        inherit_env: [],
      },
      targets: { 'fixture-test': target },
    }),
  );
  return path;
}

describe('TargetRegistry', () => {
  it('loads a bounded target and does not inherit the host environment', async () => {
    const path = await registryWith({
      description: 'Synthetic target.',
      command: process.execPath,
      args: ['fixture.js'],
      cwd: '.',
      env: { NODE_ENV: 'test' },
    });

    const registry = await TargetRegistry.load(path, {
      PATH: '/synthetic/bin',
      HY3_API_KEY: 'must-not-leak',
    });

    assert.deepEqual(registry.listIds(), ['fixture-test']);
    assert.deepEqual(registry.get('fixture-test').environment, { NODE_ENV: 'test' });
  });

  it('rejects secret-like environment inheritance', async () => {
    const path = await registryWith({
      description: 'Synthetic target.',
      command: process.execPath,
      args: [],
      cwd: '.',
      env: {},
      inherit_env: ['HY3_API_KEY'],
    });

    await assert.rejects(
      TargetRegistry.load(path, { HY3_API_KEY: 'secret' }),
      /denied by policy/,
    );
  });

  it('rejects inherited agent and signing environment variables', async () => {
    const path = await registryWith({
      description: 'Synthetic target.',
      command: process.execPath,
      args: [],
      cwd: '.',
      env: {},
      inherit_env: ['SSH_AGENT_PID'],
    });

    await assert.rejects(
      TargetRegistry.load(path, { SSH_AGENT_PID: '123' }),
      /denied by policy/,
    );
  });

  it('rejects credential-shaped fixed environment values', async () => {
    const credential = ['sk', 'abcdefghijklmnop'].join('-');
    const path = await registryWith({
      description: 'Synthetic target.',
      command: process.execPath,
      args: [],
      cwd: '.',
      env: { SAFE_VALUE: credential },
    });

    await assert.rejects(TargetRegistry.load(path), /value is denied by policy/);
  });

  it('rejects a cwd outside the allowed root', async () => {
    const path = await registryWith({
      description: 'Synthetic target.',
      command: process.execPath,
      args: [],
      cwd: '..',
      env: {},
    });

    await assert.rejects(TargetRegistry.load(path), /outside allowed roots/);
  });

  it('rejects target limits that weaken registry defaults', async () => {
    const path = await registryWith({
      description: 'Synthetic target.',
      command: process.execPath,
      args: [],
      cwd: '.',
      env: {},
      limits: { request_timeout_ms: 2000 },
    });

    await assert.rejects(TargetRegistry.load(path), /must not exceed/);
  });
});
