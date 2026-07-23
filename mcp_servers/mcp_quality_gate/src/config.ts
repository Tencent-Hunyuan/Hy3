import { z } from 'zod';

import {
  reasoningEffortValueSchema,
  type ReasoningEffort,
} from './tool-contracts.js';

const positiveIntegerFromEnvironment = (fallback: number) =>
  z
    .string()
    .regex(/^\d+$/, 'must be a positive integer')
    .transform(Number)
    .pipe(z.number().int().positive().max(300_000))
    .optional()
    .default(String(fallback));

const hy3BaseUrlSchema = z
  .string()
  .url()
  .superRefine((value, context) => {
    const parsed = new URL(value);
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'HY3_BASE_URL must use HTTP or HTTPS',
      });
    }
    if (parsed.username !== '' || parsed.password !== '') {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'HY3_BASE_URL must not contain credentials',
      });
    }
    if (parsed.search !== '' || parsed.hash !== '') {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'HY3_BASE_URL must not contain a query or fragment',
      });
    }
  });

const environmentSchema = z.object({
  HY3_API_KEY: z.preprocess(
    (value) => (value === '' ? undefined : value),
    z.string().min(1).optional(),
  ),
  HY3_BASE_URL: hy3BaseUrlSchema.default('http://127.0.0.1:8000/v1'),
  HY3_MODEL: z.string().min(1).max(128).default('hy3'),
  HY3_REASONING_EFFORT: reasoningEffortValueSchema.default('high'),
  HY3_TIMEOUT_MS: positiveIntegerFromEnvironment(60_000),
  MCPQ_TARGETS_FILE: z.preprocess(
    (value) => (value === '' ? undefined : value),
    z.string().min(1).optional(),
  ),
});

export type RuntimeConfig = {
  hy3: {
    apiKeyPresent: boolean;
    baseUrl: string;
    model: string;
    reasoningEffort: ReasoningEffort;
    timeoutMs: number;
  };
  targetsFile?: string;
};

export function loadRuntimeConfig(
  environment: NodeJS.ProcessEnv = process.env,
): RuntimeConfig {
  const parsed = environmentSchema.parse(environment);
  const base: RuntimeConfig = {
    hy3: {
      apiKeyPresent: parsed.HY3_API_KEY !== undefined,
      baseUrl: parsed.HY3_BASE_URL,
      model: parsed.HY3_MODEL,
      reasoningEffort: parsed.HY3_REASONING_EFFORT,
      timeoutMs: parsed.HY3_TIMEOUT_MS,
    },
  };

  return parsed.MCPQ_TARGETS_FILE === undefined
    ? base
    : { ...base, targetsFile: parsed.MCPQ_TARGETS_FILE };
}
