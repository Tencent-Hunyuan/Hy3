import { Ajv } from 'ajv';
import { Ajv2020 } from 'ajv/dist/2020.js';

import { isCredentialLikeKey } from '../security/redaction.js';
import { canonicalizeJson } from '../serialization/stable-json.js';
import type {
  Finding,
  InspectOutput,
  Severity,
} from '../tool-contracts.js';
import type { RuleId } from '../rules/catalog.js';

const ajvDraft07 = new Ajv({
  allErrors: true,
  strict: false,
  validateSchema: true,
});
const ajvDraft2020 = new Ajv2020({
  allErrors: true,
  strict: false,
  validateSchema: true,
});

const MINIMUM_USEFUL_DESCRIPTION_LENGTH = 8;
const MAX_TOOLS = 128;
const MAX_CONTRACT_FIELDS = 2000;
const MAX_CONTRACT_DEPTH = 32;
const MAX_CONTRACT_CHARACTERS = 1024 * 1024;

const INSTRUCTION_LIKE_TEXT =
  /\b(?:ignore|override|bypass)\b.{0,40}\b(?:instruction|policy|prompt|rule)s?\b|\b(?:reveal|expose|print)\b.{0,30}\b(?:system prompt|secret|credential)s?\b/i;
const MUTATION_SEMANTICS =
  /\b(?:create|delete|execute|modify|move|publish|remove|rename|send|set|update|upload|write)\b/i;
const DESTRUCTIVE_SEMANTICS =
  /\b(?:delete|destroy|drop|erase|overwrite|purge|remove|revoke|truncate)\b/i;

type DiscoveredTool = InspectOutput['tools'][number];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function pointerSegment(value: string): string {
  return value.replace(/~/g, '~0').replace(/\//g, '~1');
}

function excerpt(value: unknown): string | null {
  const serialized =
    typeof value === 'string' ? value : JSON.stringify(value);
  return serialized === undefined ? null : serialized.slice(0, 240);
}

function finding(
  targetId: string,
  ruleId: RuleId,
  severity: Severity,
  message: string,
  suggestion: string,
  evidencePath: string,
  toolName: string | null,
  evidence: unknown = null,
): Finding {
  return {
    rule_id: ruleId,
    severity,
    source: 'deterministic',
    message,
    suggestion,
    target_id: targetId,
    tool_name: toolName,
    evidence_path: evidencePath,
    evidence_excerpt: evidence === null ? null : excerpt(evidence),
    confidence: null,
  };
}

function isValidToolSchema(schema: Record<string, unknown>): boolean {
  try {
    if (schema.type !== 'object') {
      return false;
    }
    const dialect =
      typeof schema.$schema === 'string' ? schema.$schema : '';
    const validator = dialect.includes('2020-12')
      ? ajvDraft2020
      : ajvDraft07;
    if (validator.validateSchema(schema) !== true) {
      return false;
    }
    validator.compile(schema);
    return true;
  } catch {
    return false;
  }
}

function normalizeEnumValue(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(normalizeEnumValue);
  }
  if (isRecord(value)) {
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map((key) => [key, normalizeEnumValue(value[key])]),
    );
  }
  return typeof value === 'string' ? value.trim().toLowerCase() : value;
}

function normalizedValue(value: unknown): string {
  return JSON.stringify(normalizeEnumValue(value));
}

function exactValue(value: unknown): string {
  return JSON.stringify(canonicalizeJson(value));
}

type SchemaVisit = {
  schema: Record<string, unknown>;
  path: string;
  parameterName: string | null;
};

function visitSchema(
  root: Record<string, unknown>,
  rootPath: string,
  visitor: (visit: SchemaVisit) => void,
): void {
  const seen = new WeakSet<object>();

  const walk = (
    value: unknown,
    path: string,
    parameterName: string | null,
  ): void => {
    if (!isRecord(value) || seen.has(value)) {
      return;
    }
    seen.add(value);
    visitor({ schema: value, path, parameterName });

    const properties = value.properties;
    if (isRecord(properties)) {
      for (const [name, propertySchema] of Object.entries(properties)) {
        walk(
          propertySchema,
          `${path}/properties/${pointerSegment(name)}`,
          name,
        );
      }
    }

    const directSchemaKeys = [
      'additionalProperties',
      'contains',
      'else',
      'if',
      'items',
      'not',
      'propertyNames',
      'then',
      'unevaluatedItems',
      'unevaluatedProperties',
    ];
    for (const key of directSchemaKeys) {
      walk(value[key], `${path}/${key}`, null);
    }

    const schemaArrayKeys = ['allOf', 'anyOf', 'oneOf', 'prefixItems'];
    for (const key of schemaArrayKeys) {
      const items = value[key];
      if (Array.isArray(items)) {
        items.forEach((item, index) =>
          walk(item, `${path}/${key}/${index}`, null),
        );
      }
    }

    const schemaMapKeys = ['$defs', 'dependentSchemas', 'patternProperties'];
    for (const key of schemaMapKeys) {
      const entries = value[key];
      if (isRecord(entries)) {
        for (const [name, nested] of Object.entries(entries)) {
          walk(nested, `${path}/${key}/${pointerSegment(name)}`, null);
        }
      }
    }
  };

  walk(root, rootPath, null);
}

function auditSchema(
  targetId: string,
  tool: DiscoveredTool,
  toolIndex: number,
): Finding[] {
  const findings: Finding[] = [];
  const inputPath = `/tools/${toolIndex}/input_schema`;

  if (!isValidToolSchema(tool.input_schema)) {
    findings.push(
      finding(
        targetId,
        'SCHEMA-002',
        'error',
        `tool ${tool.name} has an invalid input JSON Schema`,
        'Use a supported JSON Schema 2020-12 structure for every input field.',
        inputPath,
        tool.name,
      ),
    );
  }

  visitSchema(tool.input_schema, inputPath, ({ schema, path, parameterName }) => {
    const properties = isRecord(schema.properties)
      ? schema.properties
      : undefined;
    const required = schema.required;
    if (Array.isArray(required) && properties !== undefined) {
      required.forEach((name, index) => {
        if (typeof name === 'string' && !(name in properties)) {
          findings.push(
            finding(
              targetId,
              'SCHEMA-003',
              'error',
              `required parameter ${name} is not declared in properties`,
              'Declare the parameter schema or remove it from required.',
              `${path}/required/${index}`,
              tool.name,
              name,
            ),
          );
        }
      });
    }

    if (parameterName !== null) {
      const description = schema.description;
      if (
        typeof description !== 'string' ||
        description.trim().length < MINIMUM_USEFUL_DESCRIPTION_LENGTH
      ) {
        findings.push(
          finding(
            targetId,
            'SCHEMA-004',
            'warning',
            `parameter ${parameterName} lacks a useful description`,
            'Describe the parameter meaning, expected format, and relevant boundaries.',
            `${path}/description`,
            tool.name,
            typeof description === 'string' ? description : null,
          ),
        );
      }
    }

    if (
      'enum' in schema &&
      (parameterName === null || !isCredentialLikeKey(parameterName))
    ) {
      const values = schema.enum;
      const normalized = Array.isArray(values)
        ? values.map(normalizedValue)
        : [];
      const hasDuplicate =
        normalized.length !== new Set(normalized).size;
      const defaultConflict =
        'default' in schema &&
        Array.isArray(values) &&
        !values.some(
          (value) => exactValue(value) === exactValue(schema.default),
        );
      if (
        !Array.isArray(values) ||
        values.length === 0 ||
        hasDuplicate ||
        defaultConflict
      ) {
        findings.push(
          finding(
            targetId,
            'SCHEMA-006',
            'error',
            `parameter ${parameterName ?? '(anonymous schema)'} has an invalid enum contract`,
            'Provide a non-empty, unique enum and ensure its default is one of the accepted values.',
            `${path}/enum`,
            tool.name,
            values,
          ),
        );
      }
    }

    if (
      parameterName !== null &&
      isCredentialLikeKey(parameterName) &&
      'default' in schema
    ) {
      findings.push(
        finding(
          targetId,
          'SAFETY-005',
          'error',
          `credential-like parameter ${parameterName} declares a default value`,
          'Remove credential defaults and require callers to supply secrets through approved runtime configuration.',
          `${path}/default`,
          tool.name,
          '[REDACTED_CREDENTIAL]',
        ),
      );
    }
  });

  if (
    tool.output_schema !== null &&
    !isValidToolSchema(tool.output_schema)
  ) {
    findings.push(
      finding(
        targetId,
        'SCHEMA-007',
        'error',
        `tool ${tool.name} has an invalid output JSON Schema`,
        'Use a supported JSON Schema 2020-12 structure for structured output.',
        `/tools/${toolIndex}/output_schema`,
        tool.name,
      ),
    );
  }

  return findings;
}

function auditDocumentationAndSafety(
  targetId: string,
  tool: DiscoveredTool,
  toolIndex: number,
): Finding[] {
  const findings: Finding[] = [];
  const description = tool.description?.trim() ?? '';
  const descriptionPath = `/tools/${toolIndex}/description`;

  if (description.length === 0) {
    findings.push(
      finding(
        targetId,
        'DOC-001',
        'warning',
        `tool ${tool.name} has no description`,
        'Explain when the tool should be selected, its result, and material side effects.',
        descriptionPath,
        tool.name,
      ),
    );
  } else {
    if (description.length < 24) {
      findings.push(
        finding(
          targetId,
          'DOC-002',
          'warning',
          `tool ${tool.name} has an overly generic description`,
          'Distinguish this tool from related tools with intent, inputs, outputs, and constraints.',
          descriptionPath,
          tool.name,
          description,
        ),
      );
    }
    if (INSTRUCTION_LIKE_TEXT.test(description)) {
      findings.push(
        finding(
          targetId,
          'DOC-006',
          'warning',
          `tool ${tool.name} contains instruction-like untrusted text`,
          'Rewrite the description as declarative contract documentation without prompt-control language.',
          descriptionPath,
          tool.name,
          description,
        ),
      );
    }
  }

  const semantics = `${tool.name.replace(/[_-]/g, ' ')} ${description}`;
  const annotations = tool.annotations ?? {};
  if (
    annotations.readOnlyHint === true &&
    MUTATION_SEMANTICS.test(semantics)
  ) {
    findings.push(
      finding(
        targetId,
        'SAFETY-001',
        'error',
        `tool ${tool.name} declares read-only behavior but describes mutation`,
        'Correct readOnlyHint or redesign the tool so its declared semantics are read-only.',
        `/tools/${toolIndex}/annotations/readOnlyHint`,
        tool.name,
        true,
      ),
    );
  }
  if (
    DESTRUCTIVE_SEMANTICS.test(semantics) &&
    annotations.destructiveHint !== true
  ) {
    findings.push(
      finding(
        targetId,
        'SAFETY-002',
        'warning',
        `destructive behavior for ${tool.name} is not declared clearly`,
        'Set destructiveHint consistently and document confirmation, scope, and recovery behavior.',
        `/tools/${toolIndex}/annotations/destructiveHint`,
        tool.name,
        annotations.destructiveHint ?? null,
      ),
    );
  }

  return findings;
}

function measureContract(value: unknown): {
  fields: number;
  depth: number;
  characters: number;
} {
  const serialized = JSON.stringify(value) ?? '';
  const stack: Array<{ value: unknown; depth: number }> = [
    { value, depth: 1 },
  ];
  const seen = new WeakSet<object>();
  let fields = 0;
  let depth = 0;

  while (stack.length > 0) {
    const current = stack.pop();
    if (current === undefined) {
      continue;
    }
    depth = Math.max(depth, current.depth);
    if (
      typeof current.value !== 'object' ||
      current.value === null ||
      seen.has(current.value)
    ) {
      continue;
    }
    seen.add(current.value);
    if (Array.isArray(current.value)) {
      for (const item of current.value) {
        stack.push({ value: item, depth: current.depth + 1 });
      }
    } else {
      const entries = Object.entries(current.value);
      fields += entries.length;
      for (const [, item] of entries) {
        stack.push({ value: item, depth: current.depth + 1 });
      }
    }
  }

  return {
    fields,
    depth,
    characters: serialized.length,
  };
}

export function runDeterministicRules(report: InspectOutput): Finding[] {
  if (report.snapshot_hash === null) {
    return [];
  }

  const findings: Finding[] = [];
  const measured = measureContract({
    protocol_version: report.protocol_version,
    server_info: report.server_info,
    tools: report.tools,
  });
  if (
    report.tools.length > MAX_TOOLS ||
    measured.fields > MAX_CONTRACT_FIELDS ||
    measured.depth > MAX_CONTRACT_DEPTH ||
    measured.characters > MAX_CONTRACT_CHARACTERS
  ) {
    findings.push(
      finding(
        report.target_id,
        'ROBUST-005',
        'warning',
        'normalized contract exceeds a deterministic audit limit, so detailed static rules were skipped',
        'Split oversized tool surfaces or reduce schema depth and descriptive payload size.',
        '/snapshot/limits',
        null,
        {
          tools: report.tools.length,
          fields: measured.fields,
          depth: measured.depth,
          characters: measured.characters,
        },
      ),
    );
    return findings;
  }

  report.tools.forEach((tool, index) => {
    findings.push(...auditSchema(report.target_id, tool, index));
    findings.push(
      ...auditDocumentationAndSafety(report.target_id, tool, index),
    );
  });

  return findings;
}
