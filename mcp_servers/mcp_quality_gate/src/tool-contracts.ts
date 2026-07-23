import { z } from 'zod';

import { RULE_IDS } from './rules/catalog.js';

export const targetIdSchema = z
  .string()
  .regex(
    /^[a-z][a-z0-9._-]{0,63}$/,
    'target_id must start with a lowercase letter and contain only lowercase letters, digits, dot, underscore, or hyphen',
  )
  .describe('Stable ID of a target declared in the startup registry.');

export const reasoningEffortSchema = z
  .enum(['no_think', 'low', 'high'])
  .default('high')
  .describe('Hy3 reasoning effort for semantic analysis.');

export const severitySchema = z.enum([
  'info',
  'warning',
  'error',
  'critical',
]);

export const ruleIdSchema = z.enum(RULE_IDS);

export const findingSchema = z.object({
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
  model_metadata: z.record(z.unknown()).nullable(),
});

export const compareInputSchema = z
  .object({
    baseline_target_id: targetIdSchema.describe(
      'Registered target representing the baseline contract.',
    ),
    current_target_id: targetIdSchema.describe(
      'Registered target representing the current contract.',
    ),
    include_non_breaking: z.boolean().default(true),
    reasoning_effort: reasoningEffortSchema,
    include_hy3: z.boolean().default(true),
  })
  .refine(
    (value) => value.baseline_target_id !== value.current_target_id,
    'baseline_target_id and current_target_id must differ',
  );

export const compareOutputSchema = z.object({
  status: z.enum(['compatible', 'breaking', 'partial']),
  baseline_hash: z.string(),
  current_hash: z.string(),
  changes: z.array(z.record(z.unknown())),
  findings: z.array(findingSchema),
  migration_plan: z.array(z.string()),
  model_metadata: z.record(z.unknown()).nullable(),
});

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

const probeCaseSchema = z.object({
  id: z.string(),
  category: z.enum(['normal', 'boundary', 'error', 'adversarial']),
  purpose: z.string(),
  arguments: z.record(z.unknown()),
  expected_outcome: z.string(),
  safety_note: z.string(),
  evidence_path: z.string(),
});

export const probeOutputSchema = z.object({
  status: z.enum(['complete', 'partial']),
  target_id: targetIdSchema,
  tool_name: z.string(),
  snapshot_hash: z.string(),
  cases: z.array(probeCaseSchema),
  rejected_case_count: z.number().int().nonnegative(),
  warnings: z.array(z.string()),
  model_metadata: z.record(z.unknown()),
});

export type InspectInput = z.infer<typeof inspectInputSchema>;
export type AuditInput = z.infer<typeof auditInputSchema>;
export type CompareInput = z.infer<typeof compareInputSchema>;
export type ProbeInput = z.infer<typeof probeInputSchema>;
export type InspectOutput = z.infer<typeof inspectOutputSchema>;
export type AuditOutput = z.infer<typeof auditOutputSchema>;
export type Finding = z.infer<typeof findingSchema>;
export type Severity = z.infer<typeof severitySchema>;
