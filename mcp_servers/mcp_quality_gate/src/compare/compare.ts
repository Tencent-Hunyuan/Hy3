import type { MigrationReviewer } from '../hy3/migration-reviewer.js';
import { inspectTarget } from '../inspector/inspect.js';
import type { ResolvedTarget } from '../target-registry.js';
import {
  compareOutputSchema,
  type CompareInput,
  type CompareOutput,
} from '../tool-contracts.js';
import { diffContracts } from './diff.js';

export class ContractComparisonError extends Error {
  constructor(
    message = 'contract comparison requires two complete target snapshots',
  ) {
    super(message);
    this.name = 'ContractComparisonError';
  }
}

export async function compareTargets(
  baselineTarget: ResolvedTarget,
  currentTarget: ResolvedTarget,
  input: CompareInput,
  migrationReviewer?: MigrationReviewer,
): Promise<CompareOutput> {
  const [baseline, current] = await Promise.all([
    inspectTarget(baselineTarget, {
      target_id: input.baseline_target_id,
      include_schemas: true,
    }),
    inspectTarget(currentTarget, {
      target_id: input.current_target_id,
      include_schemas: true,
    }),
  ]);
  if (
    baseline.snapshot_hash === null ||
    current.snapshot_hash === null
  ) {
    throw new ContractComparisonError();
  }

  const deterministic = diffContracts(
    baseline,
    current,
    input.include_non_breaking,
  );
  const hasBreakingChange = deterministic.changes.some(
    (change) => change.compatibility === 'breaking',
  );
  let migrationReview:
    | Awaited<ReturnType<MigrationReviewer['review']>>
    | undefined;
  if (input.include_hy3) {
    if (migrationReviewer !== undefined) {
      try {
        migrationReview = await migrationReviewer.review(
          baseline,
          current,
          deterministic.changes,
          input.reasoning_effort,
        );
      } catch {
        // Deterministic compatibility remains available.
      }
    }
  }

  const status: CompareOutput['status'] = hasBreakingChange
    ? 'breaking'
    : input.include_hy3 && migrationReview === undefined
      ? 'partial'
      : 'compatible';
  return compareOutputSchema.parse({
    status,
    baseline_hash: baseline.snapshot_hash,
    current_hash: current.snapshot_hash,
    changes: deterministic.changes,
    findings: [
      ...deterministic.findings,
      ...(migrationReview?.findings ?? []),
    ],
    migration_plan: migrationReview?.migrationPlan ?? [],
    model_metadata: migrationReview?.metadata ?? null,
  });
}
