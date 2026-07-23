import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, it } from 'node:test';

import {
  deduplicateFindings,
  RULE_DEDUCTION_POLICY,
  SCORING_POLICY_VERSION,
  scoreFindings,
} from '../src/audit/scoring.js';
import {
  RULE_CATALOG_VERSION,
  type RuleId,
} from '../src/rules/catalog.js';
import {
  findingSchema,
  type Finding,
  type Severity,
} from '../src/tool-contracts.js';

function finding(
  ruleId: RuleId,
  severity: Severity = 'warning',
): Finding {
  return {
    rule_id: ruleId,
    severity,
    source: 'deterministic',
    message: `Synthetic finding for ${ruleId}.`,
    suggestion: 'Apply the synthetic remediation.',
    target_id: 'fixture-test',
    tool_name: 'fixture_tool',
    evidence_path: `/synthetic/${ruleId}`,
    evidence_excerpt: null,
    confidence: null,
  };
}

describe('deterministic scoring', () => {
  it('applies each versioned rule deduction to its declared category', () => {
    for (const [ruleId, policy] of Object.entries(RULE_DEDUCTION_POLICY)) {
      assert.ok(policy);
      const result = scoreFindings([finding(ruleId as RuleId)]);

      assert.equal(result.deductions.length, 1);
      assert.equal(result.deductions[0]?.rule_id, ruleId);
      assert.equal(result.deductions[0]?.category, policy.category);
      assert.equal(result.deductions[0]?.points, policy.points);
      assert.equal(result.scorecard.overall, 100 - policy.points);
    }
  });

  it('deduplicates the same rule, target, tool, and evidence path', () => {
    const duplicate = finding('SCHEMA-002', 'error');
    const unique = deduplicateFindings([duplicate, { ...duplicate }]);
    const result = scoreFindings([duplicate, { ...duplicate }]);

    assert.equal(unique.length, 1);
    assert.equal(result.deductions.length, 1);
    assert.equal(result.scorecard.schema, 12);
    assert.equal(result.scorecard.overall, 92);
  });

  it('caps the overall score when a critical finding is present', () => {
    const result = scoreFindings([finding('PROTO-003', 'critical')]);

    assert.equal(result.scorecard.protocol, 0);
    assert.equal(result.scorecard.overall, 40);
    assert.equal(result.criticalCapApplied, true);
  });

  it('never changes the score for Hy3 findings', () => {
    const semantic: Finding = {
      ...finding('PROTO-003', 'critical'),
      source: 'hy3',
      confidence: 0.9,
    };
    const result = scoreFindings([semantic]);

    assert.equal(result.scorecard.overall, 100);
    assert.deepEqual(result.deductions, []);
    assert.equal(result.criticalCapApplied, false);
  });

  it('saturates category deductions at zero with explicit applied points', () => {
    const findings = [0, 1, 2].map((index) => ({
      ...finding('SCHEMA-002', 'error'),
      evidence_path: `/synthetic/schema/${index}`,
    }));
    const result = scoreFindings(findings);

    assert.equal(result.scorecard.schema, 0);
    assert.deepEqual(
      result.deductions.map((deduction) => deduction.points),
      [8, 8, 4],
    );
    assert.equal(
      result.deductions.reduce(
        (total, deduction) => total + deduction.points,
        0,
      ),
      20,
    );
  });

  it('rejects findings with unknown rule identifiers', () => {
    const candidate = {
      ...finding('DOC-001'),
      rule_id: 'UNKNOWN-999',
    };

    assert.equal(findingSchema.safeParse(candidate).success, false);
  });

  it('keeps the published catalogue and deduction table aligned with code', () => {
    const documentation = readFileSync(
      resolve(process.cwd(), 'docs/rule-catalog.md'),
      'utf8',
    );

    assert.ok(
      documentation.includes(
        `Catalogue version: \`${RULE_CATALOG_VERSION}\``,
      ),
    );
    assert.ok(
      documentation.includes(
        `Scoring policy \`${SCORING_POLICY_VERSION}\``,
      ),
    );
    for (const [ruleId, policy] of Object.entries(RULE_DEDUCTION_POLICY)) {
      assert.ok(policy);
      const category = policy.category.replace('_', ' ');
      assert.ok(
        documentation.includes(
          `| \`${ruleId}\` | ${category} | ${policy.points} |`,
        ),
        ruleId,
      );
    }
  });
});
