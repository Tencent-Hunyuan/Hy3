import { z } from 'zod';

import { RULE_IDS } from './rules/catalog.js';

export const targetIdSchema = z
  .string()
  .regex(
    /^[a-z][a-z0-9._-]{0,63}$/,
    'target_id must start with a lowercase letter and contain only lowercase letters, digits, dot, underscore, or hyphen',
  )
  .describe('Stable ID of a target declared in the startup registry.');

export const reasoningEffortValueSchema = z.enum([
  'no_think',
  'low',
  'high',
]);

export const reasoningEffortSchema = reasoningEffortValueSchema
  .optional()
  .describe(
    'Hy3 reasoning effort for semantic analysis. Defaults to the server HY3_REASONING_EFFORT configuration.',
  );

export const severitySchema = z.enum([
  'info',
  'warning',
  'error',
  'critical',
]);

export const ruleIdSchema = z.enum(RULE_IDS);

export const findingSchema = z
  .object({
    rule_id: ruleIdSchema,
    severity: severitySchema,
    source: z.enum(['deterministic', 'hy3']),
    message: z.string().min(1),
    suggestion: z.string().min(1),
    target_id: targetIdSchema,
    tool_name: z.string().nullable(),
    evidence_path: z.string().min(1),
    evidence_excerpt: z.string().nullable(),
    confidence: z.number().min(0).max(1).nullable(),
  })
  .superRefine((value, context) => {
    if (value.source === 'deterministic' && value.confidence !== null) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['confidence'],
        message: 'deterministic findings must use null confidence',
      });
    }
    if (value.source === 'hy3' && value.confidence === null) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['confidence'],
        message: 'Hy3 findings must include confidence',
      });
    }
  });

export const discoveredToolSchema = z.object({
  name: z.string(),
  title: z.string().nullable(),
  description: z.string().nullable(),
  input_schema: z.record(z.unknown()),
  output_schema: z.record(z.unknown()).nullable(),
  annotations: z.record(z.unknown()).nullable(),
});

export const inspectInputSchema = z.object({
  target_id: targetIdSchema,
  include_schemas: z
    .boolean()
    .default(true)
    .describe('Include normalized input and output schemas in the result.'),
  timeout_ms: z
    .number()
    .int()
    .min(500)
    .max(30_000)
    .optional()
    .describe('Optional inspection deadline capped by the target registry.'),
});

export const inspectOutputSchema = z.object({
  status: z.enum(['pass', 'fail']),
  target_id: targetIdSchema,
  protocol_version: z.string().nullable(),
  server_info: z.record(z.unknown()).nullable(),
  tools: z.array(discoveredToolSchema),
  snapshot_hash: z.string().nullable(),
  findings: z.array(findingSchema),
  duration_ms: z.number().int().nonnegative(),
});

export const auditInputSchema = z.object({
  target_id: targetIdSchema,
  reasoning_effort: reasoningEffortSchema,
  include_hy3: z
    .boolean()
    .default(true)
    .describe('Run Hy3 semantic review in addition to deterministic rules.'),
  minimum_severity: severitySchema
    .default('info')
    .describe('Minimum finding severity to include in presentation.'),
});

export const scorecardSchema = z.object({
  overall: z.number().int().min(0).max(100),
  protocol: z.number().int().min(0).max(25),
  schema: z.number().int().min(0).max(20),
  contract_clarity: z.number().int().min(0).max(20),
  safety: z.number().int().min(0).max(20),
  robustness: z.number().int().min(0).max(15),
  hy3_reviewed: z.boolean(),
});

export const semanticModelMetadataSchema = z
  .object({
    provider: z.literal('hy3'),
    model: z.string().min(1).max(128),
    reasoning_effort: reasoningEffortValueSchema,
    latency_ms: z.number().int().nonnegative(),
    attempts: z.number().int().min(1).max(2),
    usage: z
      .object({
        prompt_tokens: z.number().int().nonnegative().nullable(),
        completion_tokens: z.number().int().nonnegative().nullable(),
        total_tokens: z.number().int().nonnegative().nullable(),
      })
      .nullable(),
  })
  .strict();

export const scoreCategorySchema = z.enum([
  'protocol',
  'schema',
  'contract_clarity',
  'safety',
  'robustness',
]);

export const deductionSchema = z.object({
  rule_id: ruleIdSchema,
  category: scoreCategorySchema,
  points: z.number().int().positive(),
  target_id: targetIdSchema,
  tool_name: z.string().nullable(),
  evidence_path: z.string().min(1),
});

export const auditOutputSchema = z.object({
  status: z.enum(['pass', 'fail', 'partial']),
  target_id: targetIdSchema,
  snapshot_hash: z.string().nullable(),
  catalog_version: z.string().min(1),
  scoring_policy_version: z.string().min(1),
  critical_cap_applied: z.boolean(),
  scorecard: scorecardSchema,
  deductions: z.array(deductionSchema),
  deterministic_findings: z.array(findingSchema),
  hy3_findings: z.array(findingSchema),
  summary: z.string(),
  model_metadata: semanticModelMetadataSchema.nullable(),
});

export const compareInputSchema = z.object({
  baseline_target_id: targetIdSchema.describe(
    'Registered target representing the baseline contract.',
  ),
  current_target_id: targetIdSchema.describe(
    'Registered target representing the current contract.',
  ),
  include_non_breaking: z.boolean().default(true),
  reasoning_effort: reasoningEffortSchema,
  include_hy3: z.boolean().default(true),
});

export type JsonValue =
  | boolean
  | number
  | string
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

export const jsonValueSchema: z.ZodType<JsonValue> = z.lazy(() =>
  z.union([
    z.boolean(),
    z.number().finite(),
    z.string(),
    z.null(),
    z.array(jsonValueSchema),
    z.record(jsonValueSchema),
  ]),
);

export const contractChangeKindSchema = z.enum([
  'tool_added',
  'tool_removed',
  'tool_renamed',
  'input_required_added',
  'input_required_removed',
  'input_property_added',
  'input_property_removed',
  'input_constraint_narrowed',
  'input_constraint_widened',
  'input_enum_value_added',
  'input_enum_value_removed',
  'output_property_added',
  'output_property_removed',
  'output_constraint_changed',
  'annotation_changed',
  'text_changed',
]);

export const compatibilityRuleIdSchema = z.enum([
  'COMPAT-001',
  'COMPAT-002',
  'COMPAT-003',
  'COMPAT-004',
  'COMPAT-005',
  'COMPAT-006',
  'COMPAT-007',
  'COMPAT-008',
  'COMPAT-009',
]);

export const contractChangeSchema = z
  .object({
    id: z.string().regex(/^change-[a-f0-9]{16}$/),
    kind: contractChangeKindSchema,
    compatibility: z.enum(['breaking', 'non_breaking', 'review']),
    tool_name: z.string().min(1).max(128),
    previous_tool_name: z.string().min(1).max(128).nullable(),
    baseline_path: z.string().min(1).nullable(),
    current_path: z.string().min(1).nullable(),
    before: jsonValueSchema,
    after: jsonValueSchema,
    rule_id: compatibilityRuleIdSchema,
  })
  .strict();

export const compareOutputSchema = z
  .object({
    status: z.enum(['compatible', 'breaking', 'partial']),
    baseline_hash: z.string().regex(/^[a-f0-9]{64}$/),
    current_hash: z.string().regex(/^[a-f0-9]{64}$/),
    changes: z.array(contractChangeSchema).max(2000),
    findings: z.array(findingSchema).max(2000),
    migration_plan: z.array(z.string().min(1).max(600)).max(32),
    model_metadata: semanticModelMetadataSchema.nullable(),
  })
  .strict();

export const probeInputSchema = z.object({
  target_id: targetIdSchema,
  tool_name: z
    .string()
    .min(1)
    .max(128)
    .describe('Exact discovered tool name to generate probes for.'),
  profile: z
    .enum(['normal', 'boundary', 'error', 'adversarial', 'balanced'])
    .default('balanced'),
  max_cases: z.number().int().min(1).max(30).default(12),
  reasoning_effort: reasoningEffortSchema,
});

export const probeCategorySchema = z.enum([
  'normal',
  'boundary',
  'error',
  'adversarial',
]);

export const probeExpectedOutcomeSchema = z.enum([
  'success',
  'schema_error',
  'domain_error',
  'guarded_rejection',
]);

export const probeCaseSchema = z
  .object({
    id: z.string().regex(/^probe-[a-f0-9]{16}$/),
    category: probeCategorySchema,
    purpose: z.string().min(8).max(600),
    arguments: z.record(jsonValueSchema),
    expected_outcome: probeExpectedOutcomeSchema,
    safety_note: z.string().min(8).max(600),
    evidence_path: z.string().min(1).max(500),
  })
  .strict();

export const probeOutputSchema = z
  .object({
    status: z.enum(['complete', 'partial']),
    target_id: targetIdSchema,
    tool_name: z.string().min(1).max(128),
    snapshot_hash: z.string().regex(/^[a-f0-9]{64}$/),
    cases: z.array(probeCaseSchema).max(30),
    rejected_case_count: z.number().int().nonnegative(),
    warnings: z.array(z.string().min(1).max(600)).max(32),
    model_metadata: semanticModelMetadataSchema,
  })
  .strict();

export type InspectInput = z.infer<typeof inspectInputSchema>;
export type AuditInput = z.infer<typeof auditInputSchema>;
export type CompareInput = z.infer<typeof compareInputSchema>;
export type ProbeInput = z.infer<typeof probeInputSchema>;
export type InspectOutput = z.infer<typeof inspectOutputSchema>;
export type AuditOutput = z.infer<typeof auditOutputSchema>;
export type CompareOutput = z.infer<typeof compareOutputSchema>;
export type ContractChange = z.infer<typeof contractChangeSchema>;
export type ProbeOutput = z.infer<typeof probeOutputSchema>;
export type ProbeCase = z.infer<typeof probeCaseSchema>;
export type Finding = z.infer<typeof findingSchema>;
export type Severity = z.infer<typeof severitySchema>;
export type ReasoningEffort = z.infer<typeof reasoningEffortValueSchema>;
export type ProbeCategory = z.infer<typeof probeCategorySchema>;
export type ProbeExpectedOutcome = z.infer<
  typeof probeExpectedOutcomeSchema
>;
export type SemanticModelMetadata = z.infer<
  typeof semanticModelMetadataSchema
>;
