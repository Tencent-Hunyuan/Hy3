import type { ResolvedTarget } from '../target-registry.js';
import type { SemanticReviewer } from '../hy3/reviewer.js';
import { Hy3ReviewError } from '../hy3/errors.js';
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
  semanticReviewer?: SemanticReviewer,
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
  let semanticReview:
    | Awaited<ReturnType<SemanticReviewer['review']>>
    | undefined;
  let semanticFailureCode: string | undefined;
  if (input.include_hy3 && inspectionComplete) {
    if (semanticReviewer === undefined) {
      semanticFailureCode = 'not_configured';
    } else {
      try {
        semanticReview = await semanticReviewer.review(
          inspection,
          input.reasoning_effort,
        );
      } catch (error: unknown) {
        semanticFailureCode =
          error instanceof Hy3ReviewError ? error.code : 'unavailable';
      }
    }
  } else if (input.include_hy3) {
    semanticFailureCode = 'inspection_incomplete';
  }

  const status: AuditOutput['status'] =
    !inspectionComplete || hasBlockingFinding
      ? 'fail'
      : input.include_hy3 && semanticReview === undefined
        ? 'partial'
        : 'pass';
  const visibleFindings = deterministicFindings.filter(
    (finding) =>
      SEVERITY_RANK[finding.severity] >=
      SEVERITY_RANK[input.minimum_severity],
  );
  const semanticFindings = semanticReview?.findings ?? [];
  const visibleSemanticFindings = semanticFindings.filter(
    (finding) =>
      SEVERITY_RANK[finding.severity] >=
      SEVERITY_RANK[input.minimum_severity],
  );

  const summaryParts = [
    inspectionComplete
      ? `Deterministic audit completed with score ${scoring.scorecard.overall}/100 and ${deterministicFindings.length} finding(s).`
      : 'Inspection did not produce a contract snapshot; deterministic contract rules could not run.',
    semanticReview === undefined
      ? input.include_hy3
        ? `Hy3 semantic review did not complete (${semanticFailureCode ?? 'unavailable'}).`
        : 'Hy3 semantic review was explicitly skipped.'
      : `Hy3 semantic review completed with ${semanticFindings.length} finding(s). Hy3 summary: ${semanticReview.summary}`,
  ];
  const hiddenFindingCount =
    deterministicFindings.length -
    visibleFindings.length +
    semanticFindings.length -
    visibleSemanticFindings.length;
  if (hiddenFindingCount > 0) {
    summaryParts.push(
      `${hiddenFindingCount} finding(s) were hidden by the presentation severity filter; scoring is unchanged.`,
    );
  }

  return auditOutputSchema.parse({
    status,
    target_id: input.target_id,
    snapshot_hash: inspection.snapshot_hash,
    catalog_version: RULE_CATALOG_VERSION,
    scoring_policy_version: SCORING_POLICY_VERSION,
    critical_cap_applied: scoring.criticalCapApplied,
    scorecard: {
      ...scoring.scorecard,
      hy3_reviewed: semanticReview !== undefined,
    },
    deductions: scoring.deductions,
    deterministic_findings: visibleFindings,
    hy3_findings: visibleSemanticFindings,
    summary: summaryParts.join(' '),
    model_metadata: semanticReview?.metadata ?? null,
  });
}
