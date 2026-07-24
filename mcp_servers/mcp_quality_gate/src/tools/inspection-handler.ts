import type { CallToolResult } from '@modelcontextprotocol/sdk/types.js';

import { auditTarget } from '../audit/audit.js';
import {
  compareTargets,
  ContractComparisonError,
} from '../compare/compare.js';
import type { MigrationReviewer } from '../hy3/migration-reviewer.js';
import type { ProbeGenerator } from '../hy3/probe-generator.js';
import type { SemanticReviewer } from '../hy3/reviewer.js';
import { inspectTarget } from '../inspector/inspect.js';
import {
  generateProbeSuite,
  ProbeGenerationError,
} from '../probes/generate.js';
import { TargetRegistry, TargetRegistryError } from '../target-registry.js';
import type {
  AuditInput,
  CompareInput,
  InspectInput,
  ProbeInput,
} from '../tool-contracts.js';
import {
  createDefaultHandlers,
  type ToolHandlers,
} from './register.js';

export type QualityGateDependencies = {
  semanticReviewer?: SemanticReviewer;
  migrationReviewer?: MigrationReviewer;
  probeGenerator?: ProbeGenerator;
};

export function createToolHandlers(
  registry: TargetRegistry,
  dependencies: QualityGateDependencies = {},
): ToolHandlers {
  const handlers = createDefaultHandlers();
  const result = (
    report: Record<string, unknown>,
  ): CallToolResult => ({
    content: [
      {
        type: 'text',
        text: JSON.stringify(report, null, 2),
      },
    ],
    structuredContent: report,
  });
  const failure = (error: unknown, fallback: string): CallToolResult => {
    const message =
      error instanceof TargetRegistryError ||
      error instanceof ContractComparisonError ||
      error instanceof ProbeGenerationError
        ? error.message
        : fallback;
    return {
      isError: true,
      content: [{ type: 'text', text: message }],
    };
  };

  return {
    ...handlers,
    inspect: async (input: InspectInput): Promise<CallToolResult> => {
      try {
        const report = await inspectTarget(registry.get(input.target_id), input);
        return result({ ...report });
      } catch (error: unknown) {
        return failure(error, 'inspection could not be started');
      }
    },
    audit: async (input: AuditInput): Promise<CallToolResult> => {
      try {
        const report = await auditTarget(
          registry.get(input.target_id),
          input,
          dependencies.semanticReviewer,
        );
        return result({ ...report });
      } catch (error: unknown) {
        return failure(error, 'contract audit could not be started');
      }
    },
    compare: async (input: CompareInput): Promise<CallToolResult> => {
      try {
        if (input.baseline_target_id === input.current_target_id) {
          throw new ContractComparisonError(
            'baseline_target_id and current_target_id must differ',
          );
        }
        const report = await compareTargets(
          registry.get(input.baseline_target_id),
          registry.get(input.current_target_id),
          input,
          dependencies.migrationReviewer,
        );
        return result({ ...report });
      } catch (error: unknown) {
        return failure(error, 'contract comparison could not be completed');
      }
    },
    probes: async (input: ProbeInput): Promise<CallToolResult> => {
      try {
        const report = await generateProbeSuite(
          registry.get(input.target_id),
          input,
          dependencies.probeGenerator,
        );
        return result({ ...report });
      } catch (error: unknown) {
        return failure(error, 'probe suite could not be generated');
      }
    },
  };
}
