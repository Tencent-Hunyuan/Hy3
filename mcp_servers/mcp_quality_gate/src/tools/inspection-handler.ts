import type { CallToolResult } from '@modelcontextprotocol/sdk/types.js';

import { auditTarget } from '../audit/audit.js';
import type { SemanticReviewer } from '../hy3/reviewer.js';
import { inspectTarget } from '../inspector/inspect.js';
import { TargetRegistry, TargetRegistryError } from '../target-registry.js';
import type { AuditInput, InspectInput } from '../tool-contracts.js';
import {
  createDefaultHandlers,
  type ToolHandlers,
} from './register.js';

export function createToolHandlers(
  registry: TargetRegistry,
  semanticReviewer?: SemanticReviewer,
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
      error instanceof TargetRegistryError ? error.message : fallback;
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
          semanticReviewer,
        );
        return result({ ...report });
      } catch (error: unknown) {
        return failure(error, 'contract audit could not be started');
      }
    },
  };
}
