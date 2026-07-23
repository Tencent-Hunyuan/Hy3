import type { CallToolResult } from '@modelcontextprotocol/sdk/types.js';

import { inspectTarget } from '../inspector/inspect.js';
import { TargetRegistry, TargetRegistryError } from '../target-registry.js';
import type { InspectInput } from '../tool-contracts.js';
import {
  createDefaultHandlers,
  type ToolHandlers,
} from './register.js';

export function createToolHandlers(registry: TargetRegistry): ToolHandlers {
  const handlers = createDefaultHandlers();
  return {
    ...handlers,
    inspect: async (input: InspectInput): Promise<CallToolResult> => {
      try {
        const report = await inspectTarget(registry.get(input.target_id), input);
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(report, null, 2),
            },
          ],
          structuredContent: { ...report },
        };
      } catch (error: unknown) {
        const message =
          error instanceof TargetRegistryError
            ? error.message
            : 'inspection could not be started';
        return {
          isError: true,
          content: [{ type: 'text', text: message }],
        };
      }
    },
  };
}
