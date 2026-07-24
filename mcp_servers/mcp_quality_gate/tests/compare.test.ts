import assert from 'node:assert/strict';
import { rm } from 'node:fs/promises';
import { afterEach, describe, it } from 'node:test';

import {
  compareTargets,
  ContractComparisonError,
} from '../src/compare/compare.js';
import { diffContracts } from '../src/compare/diff.js';
import type {
  MigrationReviewer,
  MigrationReviewResult,
} from '../src/hy3/migration-reviewer.js';
import { TargetRegistry } from '../src/target-registry.js';
import type {
  CompareInput,
  InspectOutput,
} from '../src/tool-contracts.js';
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

async function comparisonRegistry(): Promise<TargetRegistry> {
  const created = await writeTestRegistry(packageRoot, {
    baseline: { fixture: 'compat-baseline-server' },
    breaking: { fixture: 'compat-breaking-server' },
    compatible: { fixture: 'compat-compatible-server' },
    polluted: { fixture: 'stdout-pollution' },
  });
  temporaryDirectories.push(created.directory);
  return TargetRegistry.load(created.path);
}

function input(
  currentTargetId: string,
  overrides: Partial<CompareInput> = {},
): CompareInput {
  return {
    baseline_target_id: 'baseline',
    current_target_id: currentTargetId,
    include_non_breaking: true,
    include_hy3: false,
    reasoning_effort: 'no_think',
    ...overrides,
  };
}

function migrationResult(targetId: string): MigrationReviewResult {
  return {
    findings: [
      {
        rule_id: 'COMPAT-008',
        severity: 'warning',
        source: 'hy3',
        message:
          'The changed search description now implies a remote tenant boundary.',
        suggestion:
          'Document the remote dependency and retain a local compatibility path.',
        target_id: targetId,
        tool_name: 'search_records',
        evidence_path: '/changes/0',
        evidence_excerpt: 'synthetic before and after descriptions',
        confidence: 0.88,
      },
    ],
    migrationPlan: [
      'Keep the prior search contract available during a documented transition.',
    ],
    metadata: {
      provider: 'hy3',
      model: 'hy3-compare-test',
      reasoning_effort: 'high',
      latency_ms: 12,
      attempts: 1,
      usage: null,
    },
  };
}

describe('compareTargets', () => {
  it('classifies compatible additions without fabricating breaking changes', async () => {
    const registry = await comparisonRegistry();

    const report = await compareTargets(
      registry.get('baseline'),
      registry.get('compatible'),
      input('compatible'),
    );

    assert.equal(report.status, 'compatible');
    assert.match(report.baseline_hash, /^[a-f0-9]{64}$/);
    assert.match(report.current_hash, /^[a-f0-9]{64}$/);
    assert.ok(report.changes.length > 0);
    assert.ok(
      report.changes.every(
        (change) => change.compatibility === 'non_breaking',
      ),
    );
    assert.ok(
      report.findings.every(
        (finding) => finding.rule_id === 'COMPAT-009',
      ),
    );
    assert.deepEqual(report.migration_plan, []);
    assert.equal(report.model_metadata, null);
  });

  it('reports every deterministic breaking compatibility family with evidence', async () => {
    const registry = await comparisonRegistry();

    const first = await compareTargets(
      registry.get('baseline'),
      registry.get('breaking'),
      input('breaking'),
    );
    const second = await compareTargets(
      registry.get('baseline'),
      registry.get('breaking'),
      input('breaking'),
    );
    const ruleIds = new Set(
      first.findings.map((finding) => finding.rule_id),
    );

    assert.equal(first.status, 'breaking');
    for (const ruleId of [
      'COMPAT-001',
      'COMPAT-002',
      'COMPAT-003',
      'COMPAT-004',
      'COMPAT-005',
      'COMPAT-006',
      'COMPAT-007',
    ] as const) {
      assert.equal(ruleIds.has(ruleId), true, ruleId);
    }
    assert.ok(
      first.changes.every(
        (change) =>
          change.baseline_path !== null ||
          change.current_path !== null,
      ),
    );
    assert.ok(
      first.findings.every(
        (finding) =>
          finding.source === 'deterministic' &&
          finding.confidence === null &&
          /^\/changes\/\d+$/u.test(finding.evidence_path),
      ),
    );
    assert.deepEqual(
      first.changes.map((change) => change.id),
      second.changes.map((change) => change.id),
    );
  });

  it('filters compatible presentation changes without hiding breaking evidence', async () => {
    const registry = await comparisonRegistry();

    const report = await compareTargets(
      registry.get('baseline'),
      registry.get('breaking'),
      input('breaking', { include_non_breaking: false }),
    );

    assert.equal(report.status, 'breaking');
    assert.ok(
      report.changes.every(
        (change) => change.compatibility !== 'non_breaking',
      ),
    );
    assert.ok(
      report.findings.every(
        (finding) => finding.rule_id !== 'COMPAT-009',
      ),
    );
  });

  it('returns partial for a compatible diff when requested Hy3 is unavailable', async () => {
    const registry = await comparisonRegistry();

    const report = await compareTargets(
      registry.get('baseline'),
      registry.get('compatible'),
      input('compatible', { include_hy3: true }),
    );

    assert.equal(report.status, 'partial');
    assert.deepEqual(report.migration_plan, []);
    assert.equal(report.model_metadata, null);
  });

  it('never lets Hy3 downgrade a deterministic breaking result', async () => {
    const registry = await comparisonRegistry();
    const reviewer: MigrationReviewer = {
      review: (_baseline, current) =>
        Promise.resolve(migrationResult(current.target_id)),
    };

    const report = await compareTargets(
      registry.get('baseline'),
      registry.get('breaking'),
      input('breaking', {
        include_hy3: true,
        reasoning_effort: 'high',
      }),
      reviewer,
    );

    assert.equal(report.status, 'breaking');
    assert.ok(
      report.findings.some(
        (finding) =>
          finding.rule_id === 'COMPAT-008' &&
          finding.source === 'hy3',
      ),
    );
    assert.equal(report.model_metadata?.model, 'hy3-compare-test');
    assert.equal(report.migration_plan.length, 1);
  });

  it('fails safely when either target cannot produce a snapshot', async () => {
    const registry = await comparisonRegistry();

    await assert.rejects(
      compareTargets(
        registry.get('baseline'),
        registry.get('polluted'),
        input('polluted'),
      ),
      ContractComparisonError,
    );
  });
});

function syntheticInspection(
  targetId: string,
  parameterSchema: Record<string, unknown>,
  parameterDescription: string,
  outputDescription: string,
): InspectOutput {
  return {
    status: 'pass',
    target_id: targetId,
    protocol_version: '2025-11-25',
    server_info: { name: targetId, version: '1.0.0' },
    tools: [
      {
        name: 'synthetic_tool',
        title: null,
        description: 'Synthetic tool contract.',
        input_schema: {
          type: 'object',
          properties: {
            value: {
              ...parameterSchema,
              description: parameterDescription,
            },
          },
        },
        output_schema: {
          type: 'object',
          properties: {
            value: {
              type: 'string',
              description: outputDescription,
            },
          },
        },
        annotations: null,
      },
    ],
    snapshot_hash: targetId === 'baseline' ? 'a'.repeat(64) : 'b'.repeat(64),
    findings: [],
    duration_ms: 1,
  };
}

describe('diffContracts schema semantics', () => {
  it('routes documentation-only schema changes to semantic review', () => {
    const baseline = syntheticInspection(
      'baseline',
      { type: 'string' },
      'Original input meaning.',
      'Original output meaning.',
    );
    const current = syntheticInspection(
      'current',
      { type: 'string' },
      'Revised input meaning.',
      'Revised output meaning.',
    );

    const result = diffContracts(baseline, current, true);

    assert.ok(result.changes.length >= 2);
    assert.ok(
      result.changes.every(
        (change) =>
          change.kind === 'text_changed' &&
          change.rule_id === 'COMPAT-008',
      ),
    );
    assert.deepEqual(result.findings, []);
  });

  it('treats disjoint types and newly introduced enums as narrowing', () => {
    const baseline = syntheticInspection(
      'baseline',
      { type: 'string' },
      'Synthetic value.',
      'Synthetic result.',
    );
    const current = syntheticInspection(
      'current',
      { type: 'number', enum: [1, 2] },
      'Synthetic value.',
      'Synthetic result.',
    );

    const result = diffContracts(baseline, current, true);

    assert.ok(
      result.changes.some(
        (change) =>
          change.rule_id === 'COMPAT-004' &&
          change.compatibility === 'breaking',
      ),
    );
    assert.ok(
      result.findings.some(
        (finding) => finding.rule_id === 'COMPAT-004',
      ),
    );
  });
});
