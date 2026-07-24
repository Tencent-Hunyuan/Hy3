import type { ProbeGenerator } from '../hy3/probe-generator.js';
import { inspectTarget } from '../inspector/inspect.js';
import type { ResolvedTarget } from '../target-registry.js';
import {
  probeOutputSchema,
  type ProbeInput,
  type ProbeOutput,
} from '../tool-contracts.js';

export class ProbeGenerationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ProbeGenerationError';
  }
}

export async function generateProbeSuite(
  target: ResolvedTarget,
  input: ProbeInput,
  generator?: ProbeGenerator,
): Promise<ProbeOutput> {
  if (generator === undefined) {
    throw new ProbeGenerationError(
      'Hy3 is required to generate a probe suite',
    );
  }
  const inspection = await inspectTarget(target, {
    target_id: input.target_id,
    include_schemas: true,
  });
  if (inspection.snapshot_hash === null) {
    throw new ProbeGenerationError(
      'probe generation requires a complete target snapshot',
    );
  }
  const toolIndex = inspection.tools.findIndex(
    (tool) => tool.name === input.tool_name,
  );
  const tool = inspection.tools[toolIndex];
  if (toolIndex < 0 || tool === undefined) {
    throw new ProbeGenerationError(
      'requested tool_name was not discovered in the target snapshot',
    );
  }

  const generated = await generator.generate(
    inspection,
    tool,
    toolIndex,
    input,
  );
  return probeOutputSchema.parse({
    status:
      generated.rejectedCaseCount > 0 ? 'partial' : 'complete',
    target_id: input.target_id,
    tool_name: input.tool_name,
    snapshot_hash: inspection.snapshot_hash,
    cases: generated.cases,
    rejected_case_count: generated.rejectedCaseCount,
    warnings: generated.warnings,
    model_metadata: generated.metadata,
  });
}
