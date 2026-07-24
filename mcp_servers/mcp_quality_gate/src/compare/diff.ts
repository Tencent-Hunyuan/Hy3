import { createHash } from 'node:crypto';

import { redactText } from '../security/redaction.js';
import {
  canonicalizeJson,
  stableJsonStringify,
} from '../serialization/stable-json.js';
import {
  contractChangeSchema,
  findingSchema,
  type ContractChange,
  type Finding,
  type InspectOutput,
  type JsonValue,
} from '../tool-contracts.js';

type ToolContract = InspectOutput['tools'][number];
type ChangeDraft = Omit<ContractChange, 'id'>;

const COMPATIBILITY_ANNOTATIONS = [
  'readOnlyHint',
  'destructiveHint',
  'idempotentHint',
  'openWorldHint',
] as const;

const LOWER_BOUND_KEYS = [
  'minItems',
  'minLength',
  'minProperties',
  'minimum',
  'exclusiveMinimum',
] as const;

const UPPER_BOUND_KEYS = [
  'maxItems',
  'maxLength',
  'maxProperties',
  'maximum',
  'exclusiveMaximum',
] as const;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function asJsonValue(value: unknown): JsonValue {
  return canonicalizeJson(value) as JsonValue;
}

function pointerSegment(value: string): string {
  return value.replace(/~/g, '~0').replace(/\//g, '~1');
}

function same(left: unknown, right: unknown): boolean {
  return stableJsonStringify(left) === stableJsonStringify(right);
}

function withoutDocumentation(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(withoutDocumentation);
  }
  if (!isRecord(value)) {
    return value;
  }
  return Object.fromEntries(
    Object.entries(value)
      .filter(
        ([key]) =>
          !['$comment', 'description', 'examples', 'title'].includes(key),
      )
      .map(([key, item]) => [key, withoutDocumentation(item)]),
  );
}

function sameSchemaStructure(left: unknown, right: unknown): boolean {
  return same(withoutDocumentation(left), withoutDocumentation(right));
}

function toolSignature(tool: ToolContract): string {
  return stableJsonStringify({
    input_schema: tool.input_schema,
    output_schema: tool.output_schema,
    annotations: tool.annotations,
  });
}

function changeId(change: ChangeDraft): string {
  const digest = createHash('sha256')
    .update(stableJsonStringify(change))
    .digest('hex')
    .slice(0, 16);
  return `change-${digest}`;
}

function draft(
  kind: ChangeDraft['kind'],
  compatibility: ChangeDraft['compatibility'],
  toolName: string,
  previousToolName: string | null,
  baselinePath: string | null,
  currentPath: string | null,
  before: unknown,
  after: unknown,
  ruleId: ChangeDraft['rule_id'],
): ChangeDraft {
  return {
    kind,
    compatibility,
    tool_name: toolName,
    previous_tool_name: previousToolName,
    baseline_path: baselinePath,
    current_path: currentPath,
    before: asJsonValue(before),
    after: asJsonValue(after),
    rule_id: ruleId,
  };
}

function propertyMap(schema: Record<string, unknown>): Record<string, unknown> {
  return isRecord(schema.properties) ? schema.properties : {};
}

function requiredSet(schema: Record<string, unknown>): Set<string> {
  return new Set(
    Array.isArray(schema.required)
      ? schema.required.filter(
          (item): item is string => typeof item === 'string',
        )
      : [],
  );
}

function typeSet(schema: Record<string, unknown>): Set<string> | null {
  if (typeof schema.type === 'string') {
    return new Set([schema.type]);
  }
  if (
    Array.isArray(schema.type) &&
    schema.type.every((item) => typeof item === 'string')
  ) {
    return new Set(schema.type);
  }
  return null;
}

function isSubset(left: ReadonlySet<string>, right: ReadonlySet<string>): boolean {
  return [...left].every((item) => right.has(item));
}

function enumMap(value: unknown): Map<string, unknown> {
  if (!Array.isArray(value)) {
    return new Map();
  }
  return new Map(
    value.map((item) => [stableJsonStringify(item), item]),
  );
}

function compareSchemaText(
  baseline: unknown,
  current: unknown,
  toolName: string,
  baselinePath: string,
  currentPath: string,
  changes: ChangeDraft[],
  depth = 0,
): void {
  if (depth > 32 || !isRecord(baseline) || !isRecord(current)) {
    return;
  }
  for (const key of ['title', 'description'] as const) {
    if (!same(baseline[key], current[key])) {
      changes.push(
        draft(
          'text_changed',
          'review',
          toolName,
          null,
          `${baselinePath}/${key}`,
          `${currentPath}/${key}`,
          baseline[key] ?? null,
          current[key] ?? null,
          'COMPAT-008',
        ),
      );
    }
  }
  const sharedKeys = Object.keys(baseline)
    .filter(
      (key) =>
        key !== 'title' &&
        key !== 'description' &&
        Object.prototype.hasOwnProperty.call(current, key),
    )
    .sort();
  for (const key of sharedKeys) {
    const previous = baseline[key];
    const next = current[key];
    if (isRecord(previous) && isRecord(next)) {
      compareSchemaText(
        previous,
        next,
        toolName,
        `${baselinePath}/${pointerSegment(key)}`,
        `${currentPath}/${pointerSegment(key)}`,
        changes,
        depth + 1,
      );
    } else if (Array.isArray(previous) && Array.isArray(next)) {
      const length = Math.min(previous.length, next.length);
      for (let index = 0; index < length; index += 1) {
        compareSchemaText(
          previous[index],
          next[index],
          toolName,
          `${baselinePath}/${pointerSegment(key)}/${index}`,
          `${currentPath}/${pointerSegment(key)}/${index}`,
          changes,
          depth + 1,
        );
      }
    }
  }
}

function compareInputSchema(
  baseline: Record<string, unknown>,
  current: Record<string, unknown>,
  toolName: string,
  baselinePath: string,
  currentPath: string,
  changes: ChangeDraft[],
  depth = 0,
): void {
  if (depth > 32) {
    return;
  }
  compareInputConstraints(
    baseline,
    current,
    toolName,
    baselinePath,
    currentPath,
    changes,
  );

  const baselineProperties = propertyMap(baseline);
  const currentProperties = propertyMap(current);
  const baselineRequired = requiredSet(baseline);
  const currentRequired = requiredSet(current);
  const propertyNames = [
    ...new Set([
      ...Object.keys(baselineProperties),
      ...Object.keys(currentProperties),
    ]),
  ].sort();

  for (const name of propertyNames) {
    const escaped = pointerSegment(name);
    const previous = baselineProperties[name];
    const next = currentProperties[name];
    const previousPath = `${baselinePath}/properties/${escaped}`;
    const nextPath = `${currentPath}/properties/${escaped}`;
    if (previous === undefined && next !== undefined) {
      if (currentRequired.has(name)) {
        changes.push(
          draft(
            'input_required_added',
            'breaking',
            toolName,
            null,
            null,
            nextPath,
            null,
            next,
            'COMPAT-003',
          ),
        );
      } else {
        changes.push(
          draft(
            'input_property_added',
            'non_breaking',
            toolName,
            null,
            null,
            nextPath,
            null,
            next,
            'COMPAT-009',
          ),
        );
      }
      continue;
    }
    if (previous !== undefined && next === undefined) {
      changes.push(
        draft(
          'input_property_removed',
          'breaking',
          toolName,
          null,
          previousPath,
          null,
          previous,
          null,
          'COMPAT-004',
        ),
      );
      continue;
    }
    if (!isRecord(previous) || !isRecord(next)) {
      if (!same(previous, next)) {
        changes.push(
          draft(
            'input_constraint_narrowed',
            'breaking',
            toolName,
            null,
            previousPath,
            nextPath,
            previous,
            next,
            'COMPAT-004',
          ),
        );
      }
      continue;
    }

    if (!baselineRequired.has(name) && currentRequired.has(name)) {
      changes.push(
        draft(
          'input_required_added',
          'breaking',
          toolName,
          null,
          `${baselinePath}/required`,
          `${currentPath}/required`,
          false,
          true,
          'COMPAT-003',
        ),
      );
    } else if (baselineRequired.has(name) && !currentRequired.has(name)) {
      changes.push(
        draft(
          'input_required_removed',
          'non_breaking',
          toolName,
          null,
          `${baselinePath}/required`,
          `${currentPath}/required`,
          true,
          false,
          'COMPAT-009',
        ),
      );
    }

    compareInputSchema(
      previous,
      next,
      toolName,
      previousPath,
      nextPath,
      changes,
      depth + 1,
    );
  }

  const previousAdditional = baseline.additionalProperties;
  const nextAdditional = current.additionalProperties;
  if (previousAdditional !== false && nextAdditional === false) {
    changes.push(
      draft(
        'input_constraint_narrowed',
        'breaking',
        toolName,
        null,
        `${baselinePath}/additionalProperties`,
        `${currentPath}/additionalProperties`,
        previousAdditional ?? true,
        false,
        'COMPAT-004',
      ),
    );
  } else if (previousAdditional === false && nextAdditional !== false) {
    changes.push(
      draft(
        'input_constraint_widened',
        'non_breaking',
        toolName,
        null,
        `${baselinePath}/additionalProperties`,
        `${currentPath}/additionalProperties`,
        false,
        nextAdditional ?? true,
        'COMPAT-009',
      ),
    );
  }
}

function compareInputConstraints(
  baseline: Record<string, unknown>,
  current: Record<string, unknown>,
  toolName: string,
  baselinePath: string,
  currentPath: string,
  changes: ChangeDraft[],
): void {
  const baselineTypes = typeSet(baseline);
  const currentTypes = typeSet(current);
  if (
    baselineTypes !== null &&
    currentTypes !== null &&
    !same([...baselineTypes].sort(), [...currentTypes].sort())
  ) {
    const narrowed = isSubset(currentTypes, baselineTypes);
    const widened = isSubset(baselineTypes, currentTypes);
    changes.push(
      draft(
        narrowed || !widened
          ? 'input_constraint_narrowed'
          : 'input_constraint_widened',
        narrowed || !widened ? 'breaking' : 'non_breaking',
        toolName,
        null,
        `${baselinePath}/type`,
        `${currentPath}/type`,
        baseline.type,
        current.type,
        narrowed || !widened ? 'COMPAT-004' : 'COMPAT-009',
      ),
    );
  } else if (baselineTypes === null && currentTypes !== null) {
    changes.push(
      draft(
        'input_constraint_narrowed',
        'breaking',
        toolName,
        null,
        `${baselinePath}/type`,
        `${currentPath}/type`,
        null,
        current.type,
        'COMPAT-004',
      ),
    );
  } else if (baselineTypes !== null && currentTypes === null) {
    changes.push(
      draft(
        'input_constraint_widened',
        'non_breaking',
        toolName,
        null,
        `${baselinePath}/type`,
        `${currentPath}/type`,
        baseline.type,
        null,
        'COMPAT-009',
      ),
    );
  }

  const baselineEnum = enumMap(baseline.enum);
  const currentEnum = enumMap(current.enum);
  if (baselineEnum.size === 0 && currentEnum.size > 0) {
    changes.push(
      draft(
        'input_constraint_narrowed',
        'breaking',
        toolName,
        null,
        `${baselinePath}/enum`,
        `${currentPath}/enum`,
        null,
        current.enum,
        'COMPAT-004',
      ),
    );
  } else if (baselineEnum.size > 0 && currentEnum.size === 0) {
    changes.push(
      draft(
        'input_constraint_widened',
        'non_breaking',
        toolName,
        null,
        `${baselinePath}/enum`,
        `${currentPath}/enum`,
        baseline.enum,
        null,
        'COMPAT-009',
      ),
    );
  } else if (baselineEnum.size > 0 && currentEnum.size > 0) {
    for (const [key, value] of baselineEnum) {
      if (!currentEnum.has(key)) {
        changes.push(
          draft(
            'input_enum_value_removed',
            'breaking',
            toolName,
            null,
            `${baselinePath}/enum`,
            `${currentPath}/enum`,
            value,
            null,
            'COMPAT-005',
          ),
        );
      }
    }
    for (const [key, value] of currentEnum) {
      if (!baselineEnum.has(key)) {
        changes.push(
          draft(
            'input_enum_value_added',
            'non_breaking',
            toolName,
            null,
            `${baselinePath}/enum`,
            `${currentPath}/enum`,
            null,
            value,
            'COMPAT-009',
          ),
        );
      }
    }
  }

  for (const key of LOWER_BOUND_KEYS) {
    const previous = baseline[key];
    const next = current[key];
    if (previous !== next) {
      const narrowed =
        typeof next === 'number' &&
        (typeof previous !== 'number' || next > previous);
      const widened =
        typeof previous === 'number' &&
        (typeof next !== 'number' || next < previous);
      if (!narrowed && !widened) {
        continue;
      }
      changes.push(
        draft(
          narrowed
            ? 'input_constraint_narrowed'
            : 'input_constraint_widened',
          narrowed ? 'breaking' : 'non_breaking',
          toolName,
          null,
          `${baselinePath}/${key}`,
          `${currentPath}/${key}`,
          previous ?? null,
          next ?? null,
          narrowed ? 'COMPAT-004' : 'COMPAT-009',
        ),
      );
    }
  }
  for (const key of UPPER_BOUND_KEYS) {
    const previous = baseline[key];
    const next = current[key];
    if (previous !== next) {
      const narrowed =
        typeof next === 'number' &&
        (typeof previous !== 'number' || next < previous);
      const widened =
        typeof previous === 'number' &&
        (typeof next !== 'number' || next > previous);
      if (!narrowed && !widened) {
        continue;
      }
      changes.push(
        draft(
          narrowed
            ? 'input_constraint_narrowed'
            : 'input_constraint_widened',
          narrowed ? 'breaking' : 'non_breaking',
          toolName,
          null,
          `${baselinePath}/${key}`,
          `${currentPath}/${key}`,
          previous ?? null,
          next ?? null,
          narrowed ? 'COMPAT-004' : 'COMPAT-009',
        ),
      );
    }
  }
  if (baseline.pattern !== current.pattern) {
    const narrowed = typeof current.pattern === 'string';
    const widened =
      typeof baseline.pattern === 'string' &&
      current.pattern === undefined;
    if (!narrowed && !widened) {
      return;
    }
    changes.push(
      draft(
        narrowed
          ? 'input_constraint_narrowed'
          : 'input_constraint_widened',
        narrowed ? 'breaking' : 'non_breaking',
        toolName,
        null,
        `${baselinePath}/pattern`,
        `${currentPath}/pattern`,
        baseline.pattern ?? null,
        current.pattern ?? null,
        narrowed ? 'COMPAT-004' : 'COMPAT-009',
      ),
    );
  }
}

function compareOutputSchema(
  baseline: Record<string, unknown> | null,
  current: Record<string, unknown> | null,
  toolName: string,
  baselinePath: string,
  currentPath: string,
  changes: ChangeDraft[],
  depth = 0,
): void {
  if (depth > 32 || same(baseline, current)) {
    return;
  }
  if (baseline === null && current !== null) {
    changes.push(
      draft(
        'output_property_added',
        'non_breaking',
        toolName,
        null,
        null,
        currentPath,
        null,
        current,
        'COMPAT-009',
      ),
    );
    return;
  }
  if (baseline !== null && current === null) {
    changes.push(
      draft(
        'output_property_removed',
        'breaking',
        toolName,
        null,
        baselinePath,
        null,
        baseline,
        null,
        'COMPAT-006',
      ),
    );
    return;
  }
  if (baseline === null || current === null) {
    return;
  }

  const rootKeysToIgnore = new Set([
    '$comment',
    'description',
    'examples',
    'properties',
    'required',
    'title',
  ]);
  const previousRootConstraints = Object.fromEntries(
    Object.entries(baseline).filter(
      ([key]) => !rootKeysToIgnore.has(key),
    ),
  );
  const nextRootConstraints = Object.fromEntries(
    Object.entries(current).filter(
      ([key]) => !rootKeysToIgnore.has(key),
    ),
  );
  if (
    !sameSchemaStructure(
      previousRootConstraints,
      nextRootConstraints,
    )
  ) {
    changes.push(
      draft(
        'output_constraint_changed',
        'breaking',
        toolName,
        null,
        baselinePath,
        currentPath,
        previousRootConstraints,
        nextRootConstraints,
        'COMPAT-006',
      ),
    );
  }

  const baselineProperties = propertyMap(baseline);
  const currentProperties = propertyMap(current);
  const baselineRequired = requiredSet(baseline);
  const currentRequired = requiredSet(current);
  const propertyNames = [
    ...new Set([
      ...Object.keys(baselineProperties),
      ...Object.keys(currentProperties),
    ]),
  ].sort();
  for (const name of propertyNames) {
    const escaped = pointerSegment(name);
    const previous = baselineProperties[name];
    const next = currentProperties[name];
    const previousPath = `${baselinePath}/properties/${escaped}`;
    const nextPath = `${currentPath}/properties/${escaped}`;
    if (previous !== undefined && next === undefined) {
      changes.push(
        draft(
          'output_property_removed',
          'breaking',
          toolName,
          null,
          previousPath,
          null,
          previous,
          null,
          'COMPAT-006',
        ),
      );
      continue;
    }
    if (previous === undefined && next !== undefined) {
      changes.push(
        draft(
          'output_property_added',
          'non_breaking',
          toolName,
          null,
          null,
          nextPath,
          null,
          next,
          'COMPAT-009',
        ),
      );
      continue;
    }
    if (!sameSchemaStructure(previous, next)) {
      changes.push(
        draft(
          'output_constraint_changed',
          'breaking',
          toolName,
          null,
          previousPath,
          nextPath,
          previous,
          next,
          'COMPAT-006',
        ),
      );
    }
    if (baselineRequired.has(name) && !currentRequired.has(name)) {
      changes.push(
        draft(
          'output_constraint_changed',
          'breaking',
          toolName,
          null,
          `${baselinePath}/required`,
          `${currentPath}/required`,
          true,
          false,
          'COMPAT-006',
        ),
      );
    }
  }
}

function annotationRisk(
  name: (typeof COMPATIBILITY_ANNOTATIONS)[number],
  previous: unknown,
  next: unknown,
): boolean {
  if (name === 'readOnlyHint' || name === 'idempotentHint') {
    return previous === true && next !== true;
  }
  return previous !== true && next === true;
}

function compareSameTool(
  baseline: ToolContract,
  current: ToolContract,
  baselineIndex: number,
  currentIndex: number,
  changes: ChangeDraft[],
): void {
  const baselineRoot = `/baseline/tools/${baselineIndex}`;
  const currentRoot = `/current/tools/${currentIndex}`;
  compareSchemaText(
    baseline.input_schema,
    current.input_schema,
    current.name,
    `${baselineRoot}/input_schema`,
    `${currentRoot}/input_schema`,
    changes,
  );
  compareSchemaText(
    baseline.output_schema,
    current.output_schema,
    current.name,
    `${baselineRoot}/output_schema`,
    `${currentRoot}/output_schema`,
    changes,
  );
  compareInputSchema(
    baseline.input_schema,
    current.input_schema,
    current.name,
    `${baselineRoot}/input_schema`,
    `${currentRoot}/input_schema`,
    changes,
  );
  compareOutputSchema(
    baseline.output_schema,
    current.output_schema,
    current.name,
    `${baselineRoot}/output_schema`,
    `${currentRoot}/output_schema`,
    changes,
  );

  const previousAnnotations = baseline.annotations ?? {};
  const nextAnnotations = current.annotations ?? {};
  for (const name of COMPATIBILITY_ANNOTATIONS) {
    const previous = previousAnnotations[name];
    const next = nextAnnotations[name];
    if (!same(previous, next)) {
      const risky = annotationRisk(name, previous, next);
      changes.push(
        draft(
          'annotation_changed',
          risky ? 'review' : 'non_breaking',
          current.name,
          null,
          `${baselineRoot}/annotations/${name}`,
          `${currentRoot}/annotations/${name}`,
          previous ?? null,
          next ?? null,
          risky ? 'COMPAT-007' : 'COMPAT-009',
        ),
      );
    }
  }

  for (const field of ['title', 'description'] as const) {
    if (!same(baseline[field], current[field])) {
      changes.push(
        draft(
          'text_changed',
          'review',
          current.name,
          null,
          `${baselineRoot}/${field}`,
          `${currentRoot}/${field}`,
          baseline[field],
          current[field],
          'COMPAT-008',
        ),
      );
    }
  }
}

function finalizeChanges(drafts: ChangeDraft[]): ContractChange[] {
  const unique = new Map<string, ContractChange>();
  for (const item of drafts) {
    const parsed = contractChangeSchema.parse({
      ...item,
      id: changeId(item),
    });
    unique.set(parsed.id, parsed);
  }
  return [...unique.values()].sort((left, right) =>
    left.id < right.id ? -1 : left.id > right.id ? 1 : 0,
  );
}

function findingMessage(change: ContractChange): {
  message: string;
  suggestion: string;
} {
  switch (change.rule_id) {
    case 'COMPAT-001':
      return {
        message: `previously exposed tool ${change.tool_name} was removed`,
        suggestion:
          'Restore the tool or provide a documented compatibility path before release.',
      };
    case 'COMPAT-002':
      return {
        message: `tool ${change.previous_tool_name ?? change.tool_name} appears to have been renamed to ${change.tool_name}`,
        suggestion:
          'Keep an alias or publish an explicit migration path for existing callers.',
      };
    case 'COMPAT-003':
      return {
        message: `tool ${change.tool_name} added a required input`,
        suggestion:
          'Make the new input optional or release a versioned compatibility boundary.',
      };
    case 'COMPAT-004':
      return {
        message: `tool ${change.tool_name} narrowed its accepted input contract`,
        suggestion:
          'Preserve previously accepted inputs or document a breaking version transition.',
      };
    case 'COMPAT-005':
      return {
        message: `tool ${change.tool_name} removed a previously accepted enum value`,
        suggestion:
          'Continue accepting the prior value or provide a versioned replacement.',
      };
    case 'COMPAT-006':
      return {
        message: `tool ${change.tool_name} removed or narrowed declared output data`,
        suggestion:
          'Preserve the prior output shape or publish a migration plan for consumers.',
      };
    case 'COMPAT-007':
      return {
        message: `tool ${change.tool_name} changed a safety annotation toward greater risk`,
        suggestion:
          'Review the new side-effect or open-world behavior and document the impact.',
      };
    case 'COMPAT-009':
      return {
        message: `tool ${change.tool_name} has a compatible contract addition or widening`,
        suggestion:
          'Document the compatible change so consumers can adopt it intentionally.',
      };
    case 'COMPAT-008':
      return {
        message: `tool ${change.tool_name} changed contract text`,
        suggestion:
          'Review whether the wording change also changes the apparent semantics.',
      };
  }
}

function evidenceExcerpt(change: ContractChange): string {
  return redactText(
    stableJsonStringify({
      baseline_path: change.baseline_path,
      current_path: change.current_path,
      before: change.before,
      after: change.after,
    }),
  ).slice(0, 240);
}

function deterministicFindings(
  changes: readonly ContractChange[],
  currentTargetId: string,
): Finding[] {
  return changes.flatMap((change, index) => {
    if (change.rule_id === 'COMPAT-008') {
      return [];
    }
    const presentation = findingMessage(change);
    return [
      findingSchema.parse({
        rule_id: change.rule_id,
        severity:
          change.rule_id === 'COMPAT-009'
            ? 'info'
            : change.rule_id === 'COMPAT-007'
              ? 'warning'
              : 'error',
        source: 'deterministic',
        message: presentation.message,
        suggestion: presentation.suggestion,
        target_id: currentTargetId,
        tool_name: change.tool_name,
        evidence_path: `/changes/${index}`,
        evidence_excerpt: evidenceExcerpt(change),
        confidence: null,
      }),
    ];
  });
}

export function diffContracts(
  baseline: InspectOutput,
  current: InspectOutput,
  includeNonBreaking: boolean,
): { changes: ContractChange[]; findings: Finding[] } {
  const drafts: ChangeDraft[] = [];
  const baselineByName = new Map(
    baseline.tools.map((tool, index) => [tool.name, { tool, index }]),
  );
  const currentByName = new Map(
    current.tools.map((tool, index) => [tool.name, { tool, index }]),
  );
  const removed = baseline.tools
    .map((tool, index) => ({ tool, index }))
    .filter(({ tool }) => !currentByName.has(tool.name));
  const added = current.tools
    .map((tool, index) => ({ tool, index }))
    .filter(({ tool }) => !baselineByName.has(tool.name));
  const pairedRemoved = new Set<string>();
  const pairedAdded = new Set<string>();

  for (const previous of removed) {
    const matches = added.filter(
      (next) =>
        !pairedAdded.has(next.tool.name) &&
        toolSignature(previous.tool) === toolSignature(next.tool),
    );
    if (matches.length !== 1) {
      continue;
    }
    const next = matches[0];
    if (next === undefined) {
      continue;
    }
    pairedRemoved.add(previous.tool.name);
    pairedAdded.add(next.tool.name);
    drafts.push(
      draft(
        'tool_renamed',
        'breaking',
        next.tool.name,
        previous.tool.name,
        `/baseline/tools/${previous.index}`,
        `/current/tools/${next.index}`,
        previous.tool.name,
        next.tool.name,
        'COMPAT-002',
      ),
    );
  }

  for (const previous of removed) {
    if (!pairedRemoved.has(previous.tool.name)) {
      drafts.push(
        draft(
          'tool_removed',
          'breaking',
          previous.tool.name,
          null,
          `/baseline/tools/${previous.index}`,
          null,
          previous.tool,
          null,
          'COMPAT-001',
        ),
      );
    }
  }
  for (const next of added) {
    if (!pairedAdded.has(next.tool.name)) {
      drafts.push(
        draft(
          'tool_added',
          'non_breaking',
          next.tool.name,
          null,
          null,
          `/current/tools/${next.index}`,
          null,
          next.tool,
          'COMPAT-009',
        ),
      );
    }
  }

  for (const [name, previous] of baselineByName) {
    const next = currentByName.get(name);
    if (next !== undefined) {
      compareSameTool(
        previous.tool,
        next.tool,
        previous.index,
        next.index,
        drafts,
      );
    }
  }

  const allChanges = finalizeChanges(drafts);
  const visibleChanges = includeNonBreaking
    ? allChanges
    : allChanges.filter(
        (change) => change.compatibility !== 'non_breaking',
      );
  return {
    changes: visibleChanges,
    findings: deterministicFindings(
      visibleChanges,
      current.target_id,
    ),
  };
}
