import { resolve } from 'node:path';

import { z } from 'zod';

import { auditTarget } from '../audit/audit.js';
import { compareTargets } from '../compare/compare.js';
import type {
  Hy3Completer,
  Hy3Completion,
  Hy3Message,
} from '../hy3/client.js';
import { Hy3ProbeGenerator } from '../hy3/probe-generator.js';
import { inspectTarget } from '../inspector/inspect.js';
import { generateProbeSuite } from '../probes/generate.js';
import type { RuleId } from '../rules/catalog.js';
import {
  ruleIdSchema,
  targetIdSchema,
} from '../tool-contracts.js';
import type {
  ProbeInput,
  ReasoningEffort,
} from '../tool-contracts.js';
import { TargetRegistry } from '../target-registry.js';

const expectedRulesSchema = z
  .array(ruleIdSchema)
  .transform((rules) => [...new Set(rules)].sort());

const relativeJsonPathSchema = z
  .string()
  .min(1)
  .max(500)
  .endsWith('.json')
  .refine(
    (value) =>
      !value.startsWith('/') &&
      !/^[A-Za-z]:[\\/]/u.test(value) &&
      !value.split(/[\\/]/u).includes('..'),
    'evaluation paths must remain relative to the package root',
  );

const expectationSchema = z
  .object({
    status: z.string().min(1).max(32),
    rules: expectedRulesSchema,
  })
  .strict();

const inspectionCaseSchema = z
  .object({
    id: z.string().regex(/^[a-z][a-z0-9-]{0,63}$/),
    kind: z.literal('inspection'),
    target_id: targetIdSchema,
    expected: expectationSchema,
  })
  .strict();

const auditCaseSchema = z
  .object({
    id: z.string().regex(/^[a-z][a-z0-9-]{0,63}$/),
    kind: z.literal('audit'),
    target_id: targetIdSchema,
    expected: expectationSchema,
  })
  .strict();

const comparisonCaseSchema = z
  .object({
    id: z.string().regex(/^[a-z][a-z0-9-]{0,63}$/),
    kind: z.literal('comparison'),
    baseline_target_id: targetIdSchema,
    current_target_id: targetIdSchema,
    include_non_breaking: z.boolean(),
    expected: expectationSchema,
  })
  .strict();

const recordedProbeCaseSchema = z
  .object({
    id: z.string().regex(/^[a-z][a-z0-9-]{0,63}$/),
    kind: z.literal('probe'),
    target_id: targetIdSchema,
    tool_name: z.string().min(1).max(128),
    profile: z.enum([
      'normal',
      'boundary',
      'error',
      'adversarial',
      'balanced',
    ]),
    max_cases: z.number().int().min(1).max(30),
    recorded_response: z.record(z.unknown()),
    expected: z
      .object({
        status: z.enum(['complete', 'partial']),
        accepted_cases: z.number().int().nonnegative(),
        rejected_cases: z.number().int().nonnegative(),
      })
      .strict(),
  })
  .strict();

const evaluationCaseSchema = z.discriminatedUnion('kind', [
  inspectionCaseSchema,
  auditCaseSchema,
  comparisonCaseSchema,
  recordedProbeCaseSchema,
]);

const metricMinimumsSchema = z
  .object({
    status_accuracy: z.number().min(0).max(1),
    exact_rule_set_accuracy: z.number().min(0).max(1),
    rule_precision: z.number().min(0).max(1),
    rule_recall: z.number().min(0).max(1),
    rule_f1: z.number().min(0).max(1),
    probe_policy_accuracy: z.number().min(0).max(1),
  })
  .strict();

export const evaluationManifestSchema = z
  .object({
    version: z.literal(1),
    targets_file: relativeJsonPathSchema,
    baseline_file: relativeJsonPathSchema,
    minimums: metricMinimumsSchema,
    cases: z.array(evaluationCaseSchema).min(1).max(100),
  })
  .strict()
  .superRefine((manifest, context) => {
    const seen = new Set<string>();
    manifest.cases.forEach((evaluationCase, index) => {
      if (seen.has(evaluationCase.id)) {
        context.addIssue({
          code: z.ZodIssueCode.custom,
          path: ['cases', index, 'id'],
          message: 'evaluation case IDs must be unique',
        });
      }
      seen.add(evaluationCase.id);
    });
  });

export type EvaluationManifest = z.infer<
  typeof evaluationManifestSchema
>;

const evaluationResultSchema = z
  .object({
    id: z.string().regex(/^[a-z][a-z0-9-]{0,63}$/),
    kind: z.enum(['inspection', 'audit', 'comparison', 'probe']),
    expected_status: z.string().min(1).max(32),
    actual_status: z.string().min(1).max(32),
    status_match: z.boolean(),
    expected_rules: expectedRulesSchema,
    actual_rules: expectedRulesSchema,
    exact_rule_match: z.boolean(),
    accepted_cases: z.number().int().nonnegative().nullable(),
    rejected_cases: z.number().int().nonnegative().nullable(),
    probe_policy_match: z.boolean().nullable(),
  })
  .strict();

const evaluationMetricsSchema = z
  .object({
    status_accuracy: z.number().min(0).max(1),
    exact_rule_set_accuracy: z.number().min(0).max(1),
    rule_precision: z.number().min(0).max(1),
    rule_recall: z.number().min(0).max(1),
    rule_f1: z.number().min(0).max(1),
    probe_policy_accuracy: z.number().min(0).max(1),
    true_positive_rules: z.number().int().nonnegative(),
    false_positive_rules: z.number().int().nonnegative(),
    false_negative_rules: z.number().int().nonnegative(),
  })
  .strict();

export const evaluationReportSchema = z
  .object({
    version: z.literal(1),
    manifest_version: z.literal(1),
    case_count: z.number().int().positive(),
    results: z.array(evaluationResultSchema).min(1).max(100),
    metrics: evaluationMetricsSchema,
    minimums: metricMinimumsSchema,
    passed: z.boolean(),
  })
  .strict()
  .superRefine((report, context) => {
    if (report.case_count !== report.results.length) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['case_count'],
        message: 'case_count must match results length',
      });
    }
  });

type EvaluationResult = z.infer<typeof evaluationResultSchema>;
export type EvaluationReport = z.infer<typeof evaluationReportSchema>;

class RecordedCompleter implements Hy3Completer {
  readonly #content: string;

  constructor(response: Record<string, unknown>) {
    this.#content = JSON.stringify(response);
  }

  complete(
    _messages: readonly Hy3Message[],
    _reasoningEffort: ReasoningEffort,
  ): Promise<Hy3Completion> {
    return Promise.resolve({
      content: this.#content,
      model: 'hy3-recorded-evaluation',
      latencyMs: 0,
      usage: null,
    });
  }
}

function sortedRules(values: readonly RuleId[]): RuleId[] {
  return [...new Set(values)].sort();
}

function exact(left: readonly string[], right: readonly string[]): boolean {
  return (
    left.length === right.length &&
    left.every((item, index) => item === right[index])
  );
}

function fraction(numerator: number, denominator: number): number {
  return denominator === 0
    ? 1
    : Number((numerator / denominator).toFixed(6));
}

async function runCase(
  registry: TargetRegistry,
  evaluationCase: z.infer<typeof evaluationCaseSchema>,
): Promise<EvaluationResult> {
  if (evaluationCase.kind === 'inspection') {
    const report = await inspectTarget(
      registry.get(evaluationCase.target_id),
      {
        target_id: evaluationCase.target_id,
        include_schemas: true,
      },
    );
    const expectedRules = evaluationCase.expected.rules;
    const actualRules = sortedRules(
      report.findings.map((finding) => finding.rule_id),
    );
    return {
      id: evaluationCase.id,
      kind: evaluationCase.kind,
      expected_status: evaluationCase.expected.status,
      actual_status: report.status,
      status_match: report.status === evaluationCase.expected.status,
      expected_rules: expectedRules,
      actual_rules: actualRules,
      exact_rule_match: exact(expectedRules, actualRules),
      accepted_cases: null,
      rejected_cases: null,
      probe_policy_match: null,
    };
  }
  if (evaluationCase.kind === 'audit') {
    const report = await auditTarget(
      registry.get(evaluationCase.target_id),
      {
        target_id: evaluationCase.target_id,
        include_hy3: false,
        minimum_severity: 'info',
      },
    );
    const expectedRules = evaluationCase.expected.rules;
    const actualRules = sortedRules(
      report.deterministic_findings.map(
        (finding) => finding.rule_id,
      ),
    );
    return {
      id: evaluationCase.id,
      kind: evaluationCase.kind,
      expected_status: evaluationCase.expected.status,
      actual_status: report.status,
      status_match: report.status === evaluationCase.expected.status,
      expected_rules: expectedRules,
      actual_rules: actualRules,
      exact_rule_match: exact(expectedRules, actualRules),
      accepted_cases: null,
      rejected_cases: null,
      probe_policy_match: null,
    };
  }
  if (evaluationCase.kind === 'comparison') {
    const report = await compareTargets(
      registry.get(evaluationCase.baseline_target_id),
      registry.get(evaluationCase.current_target_id),
      {
        baseline_target_id: evaluationCase.baseline_target_id,
        current_target_id: evaluationCase.current_target_id,
        include_non_breaking: evaluationCase.include_non_breaking,
        include_hy3: false,
      },
    );
    const expectedRules = evaluationCase.expected.rules;
    const actualRules = sortedRules(
      report.findings.map((finding) => finding.rule_id),
    );
    return {
      id: evaluationCase.id,
      kind: evaluationCase.kind,
      expected_status: evaluationCase.expected.status,
      actual_status: report.status,
      status_match: report.status === evaluationCase.expected.status,
      expected_rules: expectedRules,
      actual_rules: actualRules,
      exact_rule_match: exact(expectedRules, actualRules),
      accepted_cases: null,
      rejected_cases: null,
      probe_policy_match: null,
    };
  }

  const probeInput: ProbeInput = {
    target_id: evaluationCase.target_id,
    tool_name: evaluationCase.tool_name,
    profile: evaluationCase.profile,
    max_cases: evaluationCase.max_cases,
    reasoning_effort: 'no_think',
  };
  const report = await generateProbeSuite(
    registry.get(evaluationCase.target_id),
    probeInput,
    new Hy3ProbeGenerator(
      new RecordedCompleter(evaluationCase.recorded_response),
      'no_think',
    ),
  );
  const policyMatch =
    report.status === evaluationCase.expected.status &&
    report.cases.length === evaluationCase.expected.accepted_cases &&
    report.rejected_case_count ===
      evaluationCase.expected.rejected_cases;
  return evaluationResultSchema.parse({
    id: evaluationCase.id,
    kind: evaluationCase.kind,
    expected_status: evaluationCase.expected.status,
    actual_status: report.status,
    status_match: report.status === evaluationCase.expected.status,
    expected_rules: [],
    actual_rules: [],
    exact_rule_match: true,
    accepted_cases: report.cases.length,
    rejected_cases: report.rejected_case_count,
    probe_policy_match: policyMatch,
  });
}

export async function runEvaluation(
  packageRoot: string,
  manifest: EvaluationManifest,
): Promise<EvaluationReport> {
  const registry = await TargetRegistry.load(
    resolve(packageRoot, manifest.targets_file),
  );
  const results: EvaluationResult[] = [];
  for (const evaluationCase of manifest.cases) {
    results.push(await runCase(registry, evaluationCase));
  }

  let truePositiveRules = 0;
  let falsePositiveRules = 0;
  let falseNegativeRules = 0;
  for (const result of results) {
    const expected = new Set(
      result.expected_rules.map((rule) => `${result.id}:${rule}`),
    );
    const actual = new Set(
      result.actual_rules.map((rule) => `${result.id}:${rule}`),
    );
    for (const label of actual) {
      if (expected.has(label)) {
        truePositiveRules += 1;
      } else {
        falsePositiveRules += 1;
      }
    }
    for (const label of expected) {
      if (!actual.has(label)) {
        falseNegativeRules += 1;
      }
    }
  }

  const precision = fraction(
    truePositiveRules,
    truePositiveRules + falsePositiveRules,
  );
  const recall = fraction(
    truePositiveRules,
    truePositiveRules + falseNegativeRules,
  );
  const f1 =
    precision + recall === 0
      ? 0
      : Number(
          ((2 * precision * recall) / (precision + recall)).toFixed(6),
        );
  const probeResults = results.filter(
    (result) => result.probe_policy_match !== null,
  );
  const metrics = {
    status_accuracy: fraction(
      results.filter((result) => result.status_match).length,
      results.length,
    ),
    exact_rule_set_accuracy: fraction(
      results.filter((result) => result.exact_rule_match).length,
      results.length,
    ),
    rule_precision: precision,
    rule_recall: recall,
    rule_f1: f1,
    probe_policy_accuracy: fraction(
      probeResults.filter(
        (result) => result.probe_policy_match === true,
      ).length,
      probeResults.length,
    ),
    true_positive_rules: truePositiveRules,
    false_positive_rules: falsePositiveRules,
    false_negative_rules: falseNegativeRules,
  };
  const passed = (
    Object.entries(manifest.minimums) as Array<
      [
        keyof z.infer<typeof metricMinimumsSchema>,
        number,
      ]
    >
  ).every(([name, minimum]) => metrics[name] >= minimum);

  return evaluationReportSchema.parse({
    version: 1,
    manifest_version: manifest.version,
    case_count: results.length,
    results,
    metrics,
    minimums: manifest.minimums,
    passed,
  });
}
