import assert from 'node:assert/strict';
import { rm } from 'node:fs/promises';
import { afterEach, describe, it } from 'node:test';

import { auditTarget } from '../src/audit/audit.js';
import { Hy3ReviewError } from '../src/hy3/errors.js';
import type {
  SemanticReviewer,
  SemanticReviewResult,
} from '../src/hy3/reviewer.js';
import { TargetRegistry } from '../src/target-registry.js';
import type { AuditInput } from '../src/tool-contracts.js';
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

async function registryFor(
  targets: Parameters<typeof writeTestRegistry>[1],
): Promise<TargetRegistry> {
  const created = await writeTestRegistry(packageRoot, targets);
  temporaryDirectories.push(created.directory);
  return TargetRegistry.load(created.path);
}

function auditInput(
  targetId: string,
  overrides: Partial<AuditInput> = {},
): AuditInput {
  return {
    target_id: targetId,
    reasoning_effort: 'no_think',
    include_hy3: false,
    minimum_severity: 'info',
    ...overrides,
  };
}

function successfulSemanticReview(targetId: string): SemanticReviewResult {
  return {
    findings: [
      {
        rule_id: 'SAFETY-001',
        severity: 'error',
        source: 'hy3',
        message:
          'The synthetic semantic review identified a possible annotation conflict.',
        suggestion:
          'Review the annotation against the documented operation before release.',
        target_id: targetId,
        tool_name: 'fixture_echo',
        evidence_path: '/tools/0/description',
        evidence_excerpt:
          'Return the provided synthetic text unchanged for protocol tests.',
        confidence: 0.91,
      },
    ],
    summary: 'One advisory semantic issue was identified.',
    metadata: {
      provider: 'hy3',
      model: 'hy3-test',
      reasoning_effort: 'high',
      latency_ms: 25,
      attempts: 1,
      usage: {
        prompt_tokens: 20,
        completion_tokens: 10,
        total_tokens: 30,
      },
    },
  };
}

describe('auditTarget', () => {
  it('passes a documented fixture with a reproducible perfect score', async () => {
    const registry = await registryFor({
      good: { fixture: 'good-server' },
    });

    const first = await auditTarget(
      registry.get('good'),
      auditInput('good'),
    );
    const second = await auditTarget(
      registry.get('good'),
      auditInput('good'),
    );

    assert.equal(first.status, 'pass');
    assert.equal(first.scorecard.overall, 100);
    assert.equal(first.scorecard.hy3_reviewed, false);
    assert.equal(first.catalog_version, '1.0.0');
    assert.equal(first.scoring_policy_version, '1.0.0');
    assert.equal(first.critical_cap_applied, false);
    assert.deepEqual(first.deterministic_findings, []);
    assert.deepEqual(first.deductions, []);
    assert.equal(first.snapshot_hash, second.snapshot_hash);
    assert.deepEqual(first.scorecard, second.scorecard);
  });

  it('reports every implemented static rule against the negative fixture', async () => {
    const registry = await registryFor({
      bad: { fixture: 'audit-bad-server' },
    });

    const report = await auditTarget(
      registry.get('bad'),
      auditInput('bad'),
    );
    const ruleIds = [
      ...new Set(
        report.deterministic_findings.map((finding) => finding.rule_id),
      ),
    ].sort();

    assert.equal(report.status, 'fail');
    assert.deepEqual(ruleIds, [
      'DOC-001',
      'DOC-002',
      'DOC-006',
      'SAFETY-001',
      'SAFETY-002',
      'SAFETY-005',
      'SCHEMA-002',
      'SCHEMA-003',
      'SCHEMA-004',
      'SCHEMA-006',
      'SCHEMA-007',
    ]);
    assert.ok(report.scorecard.overall < 100);
    assert.ok(report.deductions.length > 0);
    assert.ok(
      report.deterministic_findings.every(
        (finding) =>
          finding.source === 'deterministic' &&
          finding.confidence === null &&
          finding.evidence_path.startsWith('/'),
      ),
    );
  });

  it('keeps status and scoring stable when presentation filtering hides findings', async () => {
    const registry = await registryFor({
      bad: { fixture: 'audit-bad-server' },
    });

    const complete = await auditTarget(
      registry.get('bad'),
      auditInput('bad'),
    );
    const filtered = await auditTarget(
      registry.get('bad'),
      auditInput('bad', { minimum_severity: 'critical' }),
    );

    assert.equal(filtered.status, 'fail');
    assert.deepEqual(filtered.scorecard, complete.scorecard);
    assert.deepEqual(filtered.deductions, complete.deductions);
    assert.deepEqual(filtered.deterministic_findings, []);
    assert.match(filtered.summary, /scoring is unchanged/);
  });

  it('returns partial when Hy3 was requested but deterministic audit passes', async () => {
    const registry = await registryFor({
      good: { fixture: 'good-server' },
    });

    const report = await auditTarget(
      registry.get('good'),
      auditInput('good', {
        include_hy3: true,
        reasoning_effort: 'high',
      }),
    );

    assert.equal(report.status, 'partial');
    assert.equal(report.scorecard.overall, 100);
    assert.deepEqual(report.hy3_findings, []);
    assert.equal(report.model_metadata, null);
    assert.match(report.summary, /not_configured/);
  });

  it('keeps deterministic failure precedence when Hy3 was requested', async () => {
    const registry = await registryFor({
      bad: { fixture: 'audit-bad-server' },
    });

    const report = await auditTarget(
      registry.get('bad'),
      auditInput('bad', {
        include_hy3: true,
        reasoning_effort: 'high',
      }),
    );

    assert.equal(report.status, 'fail');
    assert.equal(report.scorecard.hy3_reviewed, false);
    assert.match(report.summary, /not_configured/);
  });

  it('includes validated Hy3 findings without changing deterministic scoring', async () => {
    const registry = await registryFor({
      good: { fixture: 'good-server' },
    });
    const reviewer: SemanticReviewer = {
      review: () =>
        Promise.resolve(successfulSemanticReview('good')),
    };

    const report = await auditTarget(
      registry.get('good'),
      auditInput('good', {
        include_hy3: true,
        reasoning_effort: 'high',
      }),
      reviewer,
    );

    assert.equal(report.status, 'pass');
    assert.equal(report.scorecard.overall, 100);
    assert.equal(report.scorecard.hy3_reviewed, true);
    assert.equal(report.deductions.length, 0);
    assert.equal(report.hy3_findings.length, 1);
    assert.equal(report.hy3_findings[0]?.source, 'hy3');
    assert.equal(report.hy3_findings[0]?.severity, 'error');
    assert.equal(report.model_metadata?.model, 'hy3-test');
    assert.match(report.summary, /Hy3 semantic review completed/);
  });

  it('degrades safely when the Hy3 reviewer times out', async () => {
    const registry = await registryFor({
      good: { fixture: 'good-server' },
    });
    const reviewer: SemanticReviewer = {
      review: () => Promise.reject(new Hy3ReviewError('timeout')),
    };

    const report = await auditTarget(
      registry.get('good'),
      auditInput('good', { include_hy3: true }),
      reviewer,
    );

    assert.equal(report.status, 'partial');
    assert.equal(report.scorecard.overall, 100);
    assert.equal(report.scorecard.hy3_reviewed, false);
    assert.deepEqual(report.hy3_findings, []);
    assert.equal(report.model_metadata, null);
    assert.match(report.summary, /\(timeout\)/);
  });

  it('does not call Hy3 when semantic review is disabled', async () => {
    const registry = await registryFor({
      good: { fixture: 'good-server' },
    });
    let calls = 0;
    const reviewer: SemanticReviewer = {
      review: () => {
        calls += 1;
        return Promise.resolve(successfulSemanticReview('good'));
      },
    };

    const report = await auditTarget(
      registry.get('good'),
      auditInput('good', { include_hy3: false }),
      reviewer,
    );

    assert.equal(report.status, 'pass');
    assert.equal(report.scorecard.hy3_reviewed, false);
    assert.equal(calls, 0);
  });

  it('preserves protocol findings when no snapshot can be produced', async () => {
    const registry = await registryFor({
      polluted: { fixture: 'stdout-pollution' },
    });

    const report = await auditTarget(
      registry.get('polluted'),
      auditInput('polluted'),
    );

    assert.equal(report.status, 'fail');
    assert.equal(report.snapshot_hash, null);
    assert.ok(
      report.deterministic_findings.some(
        (finding) => finding.rule_id === 'PROTO-002',
      ),
    );
    assert.ok(
      report.deductions.some(
        (deduction) => deduction.rule_id === 'PROTO-002',
      ),
    );
  });

  it('scores discovery identity, naming, duplication, and schema findings', async () => {
    const registry = await registryFor({
      defects: { fixture: 'discovery-defects-server' },
    });

    const report = await auditTarget(
      registry.get('defects'),
      auditInput('defects'),
    );
    const ruleIds = new Set(
      report.deterministic_findings.map((finding) => finding.rule_id),
    );

    assert.equal(report.status, 'fail');
    assert.ok(report.snapshot_hash);
    for (const ruleId of [
      'PROTO-005',
      'PROTO-007',
      'PROTO-008',
      'SCHEMA-001',
      'SCHEMA-002',
    ] as const) {
      assert.equal(ruleIds.has(ruleId), true, ruleId);
      assert.equal(
        report.deductions.some(
          (deduction) => deduction.rule_id === ruleId,
        ),
        true,
        ruleId,
      );
    }
  });

  it('preserves an invalid tools/list result as a scored protocol finding', async () => {
    const registry = await registryFor({
      invalid: {
        fixture: 'discovery-defects-server',
        env: { FIXTURE_INVALID_LIST: '1' },
      },
    });

    const report = await auditTarget(
      registry.get('invalid'),
      auditInput('invalid'),
    );

    assert.equal(report.status, 'fail');
    assert.equal(report.snapshot_hash, null);
    assert.ok(
      report.deterministic_findings.some(
        (finding) => finding.rule_id === 'PROTO-006',
      ),
    );
    assert.ok(
      report.deductions.some(
        (deduction) => deduction.rule_id === 'PROTO-006',
      ),
    );
  });

  it('reports deterministic contract size limits', async () => {
    const registry = await registryFor({
      oversized: {
        fixture: 'oversized-contract-server',
      },
    });

    const report = await auditTarget(
      registry.get('oversized'),
      auditInput('oversized'),
    );

    assert.equal(report.status, 'pass');
    assert.ok(
      report.deterministic_findings.some(
        (finding) => finding.rule_id === 'ROBUST-005',
      ),
    );
    assert.ok(report.scorecard.robustness < 15);
  });
});
