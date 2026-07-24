import assert from 'node:assert/strict';
import { rm } from 'node:fs/promises';
import { afterEach, describe, it } from 'node:test';

import type { ProbeGenerator } from '../src/hy3/probe-generator.js';
import {
  generateProbeSuite,
  ProbeGenerationError,
} from '../src/probes/generate.js';
import { TargetRegistry } from '../src/target-registry.js';
import type { ProbeInput } from '../src/tool-contracts.js';
import { writeTestRegistry } from './helpers/registry.js';

const packageRoot = process.cwd();
const temporaryDirectories: string[] = [];

afterEach(async () => {
  await Promise.all(
    temporaryDirectories.splice(0).map(async (path) =>
      rm(path, { recursive: true }),
    ),
  );
});

async function registryForProbes(): Promise<TargetRegistry> {
  const created = await writeTestRegistry(packageRoot, {
    good: { fixture: 'good-server' },
    polluted: { fixture: 'stdout-pollution' },
  });
  temporaryDirectories.push(created.directory);
  return TargetRegistry.load(created.path);
}

function input(
  targetId = 'good',
  toolName = 'fixture_echo',
): ProbeInput {
  return {
    target_id: targetId,
    tool_name: toolName,
    profile: 'balanced',
    max_cases: 12,
    reasoning_effort: 'no_think',
  };
}

function generator(rejectedCaseCount = 0): ProbeGenerator {
  return {
    generate: (_inspection, _tool, toolIndex) =>
      Promise.resolve({
        cases: [
          {
            id: 'probe-0123456789abcdef',
            category: 'normal',
            purpose:
              'Verify an ordinary harmless synthetic echo operation.',
            arguments: { text: 'synthetic hello' },
            expected_outcome: 'success',
            safety_note:
              'This generated case contains inert synthetic data only.',
            evidence_path: `/tools/${toolIndex}/input_schema/properties/text`,
          },
        ],
        rejectedCaseCount,
        warnings: [
          'Generated probes are inert data and were not executed by the quality gate.',
        ],
        metadata: {
          provider: 'hy3',
          model: 'hy3-probe-orchestrator-test',
          reasoning_effort: 'no_think',
          latency_ms: 4,
          attempts: 1,
          usage: null,
        },
      }),
  };
}

describe('generateProbeSuite', () => {
  it('returns validated structured probe output without executing a target tool', async () => {
    const registry = await registryForProbes();

    const report = await generateProbeSuite(
      registry.get('good'),
      input(),
      generator(),
    );

    assert.equal(report.status, 'complete');
    assert.equal(report.target_id, 'good');
    assert.equal(report.tool_name, 'fixture_echo');
    assert.equal(report.cases.length, 1);
    assert.equal(report.rejected_case_count, 0);
    assert.equal(
      report.model_metadata.model,
      'hy3-probe-orchestrator-test',
    );
  });

  it('returns partial when local validation rejected candidates', async () => {
    const registry = await registryForProbes();

    const report = await generateProbeSuite(
      registry.get('good'),
      input(),
      generator(2),
    );

    assert.equal(report.status, 'partial');
    assert.equal(report.rejected_case_count, 2);
  });

  it('requires Hy3 and an exact discovered tool name', async () => {
    const registry = await registryForProbes();

    await assert.rejects(
      generateProbeSuite(registry.get('good'), input()),
      ProbeGenerationError,
    );
    await assert.rejects(
      generateProbeSuite(
        registry.get('good'),
        input('good', 'missing_tool'),
        generator(),
      ),
      (error: unknown) =>
        error instanceof ProbeGenerationError &&
        /tool_name/u.test(error.message),
    );
  });

  it('fails safely when inspection cannot produce a snapshot', async () => {
    const registry = await registryForProbes();

    await assert.rejects(
      generateProbeSuite(
        registry.get('polluted'),
        input('polluted'),
        generator(),
      ),
      (error: unknown) =>
        error instanceof ProbeGenerationError &&
        /snapshot/u.test(error.message),
    );
  });
});
