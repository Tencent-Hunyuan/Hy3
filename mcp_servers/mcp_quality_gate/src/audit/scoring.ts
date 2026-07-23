import type { Finding } from '../tool-contracts.js';
import type { RuleId } from '../rules/catalog.js';
import { stableJsonStringify } from '../serialization/stable-json.js';

export const SCORING_POLICY_VERSION = '1.0.0';
export const CRITICAL_OVERALL_CAP = 40;

export const SCORE_CATEGORY_WEIGHTS = {
  protocol: 25,
  schema: 20,
  contract_clarity: 20,
  safety: 20,
  robustness: 15,
} as const;

export type ScoreCategory = keyof typeof SCORE_CATEGORY_WEIGHTS;

type RuleDeductionPolicy = {
  category: ScoreCategory;
  points: number;
};

export const RULE_DEDUCTION_POLICY: Readonly<
  Partial<Record<RuleId, RuleDeductionPolicy>>
> = {
  'PROTO-001': { category: 'protocol', points: 25 },
  'PROTO-002': { category: 'protocol', points: 8 },
  'PROTO-003': { category: 'protocol', points: 25 },
  'PROTO-004': { category: 'protocol', points: 10 },
  'PROTO-005': { category: 'protocol', points: 2 },
  'PROTO-006': { category: 'protocol', points: 10 },
  'PROTO-007': { category: 'protocol', points: 6 },
  'PROTO-008': { category: 'protocol', points: 2 },
  'SCHEMA-001': { category: 'schema', points: 8 },
  'SCHEMA-002': { category: 'schema', points: 8 },
  'SCHEMA-003': { category: 'schema', points: 6 },
  'SCHEMA-004': { category: 'schema', points: 2 },
  'SCHEMA-006': { category: 'schema', points: 6 },
  'SCHEMA-007': { category: 'schema', points: 8 },
  'DOC-001': { category: 'contract_clarity', points: 5 },
  'DOC-002': { category: 'contract_clarity', points: 3 },
  'DOC-006': { category: 'contract_clarity', points: 4 },
  'SAFETY-001': { category: 'safety', points: 8 },
  'SAFETY-002': { category: 'safety', points: 5 },
  'SAFETY-005': { category: 'safety', points: 10 },
  'ROBUST-001': { category: 'robustness', points: 8 },
  'ROBUST-002': { category: 'robustness', points: 8 },
  'ROBUST-003': { category: 'robustness', points: 15 },
  'ROBUST-004': { category: 'robustness', points: 3 },
  'ROBUST-005': { category: 'robustness', points: 4 },
};

export type AppliedDeduction = {
  rule_id: RuleId;
  category: ScoreCategory;
  points: number;
  target_id: string;
  tool_name: string | null;
  evidence_path: string;
};

function findingKey(finding: Finding): string {
  return stableJsonStringify([
    finding.rule_id,
    finding.target_id,
    finding.tool_name ?? '',
    finding.evidence_path,
  ]);
}

export function deduplicateFindings(findings: readonly Finding[]): Finding[] {
  const unique = new Map<string, Finding>();
  for (const finding of findings) {
    const key = findingKey(finding);
    if (!unique.has(key)) {
      unique.set(key, finding);
    }
  }
  return [...unique.values()].sort((left, right) => {
    const leftKey = findingKey(left);
    const rightKey = findingKey(right);
    return leftKey < rightKey ? -1 : leftKey > rightKey ? 1 : 0;
  });
}

export function scoreFindings(findings: readonly Finding[]): {
  scorecard: {
    overall: number;
    protocol: number;
    schema: number;
    contract_clarity: number;
    safety: number;
    robustness: number;
    hy3_reviewed: false;
  };
  deductions: AppliedDeduction[];
  criticalCapApplied: boolean;
} {
  const remaining: Record<ScoreCategory, number> = {
    ...SCORE_CATEGORY_WEIGHTS,
  };
  const deductions: AppliedDeduction[] = [];
  const deterministicFindings = deduplicateFindings(
    findings.filter((finding) => finding.source === 'deterministic'),
  );

  for (const finding of deterministicFindings) {
    const policy = RULE_DEDUCTION_POLICY[finding.rule_id];
    if (policy === undefined) {
      continue;
    }
    const points = Math.min(policy.points, remaining[policy.category]);
    if (points === 0) {
      continue;
    }
    remaining[policy.category] -= points;
    deductions.push({
      rule_id: finding.rule_id,
      category: policy.category,
      points,
      target_id: finding.target_id,
      tool_name: finding.tool_name,
      evidence_path: finding.evidence_path,
    });
  }

  const uncappedOverall = Object.values(remaining).reduce(
    (total, value) => total + value,
    0,
  );
  const hasCritical = deterministicFindings.some(
    (finding) => finding.severity === 'critical',
  );
  const criticalCapApplied =
    hasCritical && uncappedOverall > CRITICAL_OVERALL_CAP;
  const overall = criticalCapApplied
    ? CRITICAL_OVERALL_CAP
    : uncappedOverall;

  return {
    scorecard: {
      overall,
      protocol: remaining.protocol,
      schema: remaining.schema,
      contract_clarity: remaining.contract_clarity,
      safety: remaining.safety,
      robustness: remaining.robustness,
      hy3_reviewed: false,
    },
    deductions,
    criticalCapApplied,
  };
}
