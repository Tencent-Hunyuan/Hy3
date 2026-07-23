import type { ResolvedTarget } from '../target-registry.js';
import {
  auditOutputSchema,
  type AuditInput,
  type AuditOutput,
  type Severity,
} from '../tool-contracts.js';
import { inspectTarget } from '../inspector/inspect.js';
import { RULE_CATALOG_VERSION } from '../rules/catalog.js';
import { runDeterministicRules } from './deterministic.js';
import {
  deduplicateFindings,
  scoreFindings,
  SCORING_POLICY_VERSION,
} from './scoring.js';

const SEVERITY_RANK: Record<Severity, number> = {
  info: 0,
  warning: 1,
  error: 2,
  critical: 3,
};

export async function auditTarget(
  target: ResolvedTarget,
  input: AuditInput,
): Promise<AuditOutput> {
  const inspection = await inspectTarget(target, {
    target_id: input.target_id,
    include_schemas: true,
  });
  const deterministicFindings = deduplicateFindings([
    ...inspection.findings,
    ...runDeterministicRules(inspection),
  ]);
  const scoring = scoreFindings(deterministicFindings);
  const hasBlockingFinding = deterministicFindings.some(
    (finding) =>
      finding.severity === 'error' || finding.severity === 'critical',
  );
  const inspectionComplete = inspection.snapshot_hash !== null;
  const status: AuditOutput['status'] =
    !inspectionComplete || hasBlockingFinding
      ? 'fail'
      : input.include_hy3
        ? 'partial'
        : 'pass';
  const visibleFindings = deterministicFindings.filter(
    (finding) =>
      SEVERITY_RANK[finding.severity] >=
      SEVERITY_RANK[input.minimum_severity],
  );

  const summaryParts = [
    inspectionComplete
      ? `Deterministic audit completed with score ${scoring.scorecard.overall}/100 and ${deterministicFindings.length} finding(s).`
      : 'Inspection did not produce a contract snapshot; deterministic contract rules could not run.',
    input.include_hy3
      ? `Hy3 semantic review was requested with ${input.reasoning_effort} effort but is unavailable until Stage 5.`
      : 'Hy3 semantic review was explicitly skipped.',
  ];
  if (visibleFindings.length !== deterministicFindings.length) {
    summaryParts.push(
      `${deterministicFindings.length - visibleFindings.length} finding(s) were hidden by the presentation severity filter; scoring is unchanged.`,
    );
  }

  return auditOutputSchema.parse({
    status,
    target_id: input.target_id,
    snapshot_hash: inspection.snapshot_hash,
    catalog_version: RULE_CATALOG_VERSION,
    scoring_policy_version: SCORING_POLICY_VERSION,
    critical_cap_applied: scoring.criticalCapApplied,
    scorecard: scoring.scorecard,
    deductions: scoring.deductions,
    deterministic_findings: visibleFindings,
    hy3_findings: [],
    summary: summaryParts.join(' '),
    model_metadata: null,
  });
}
