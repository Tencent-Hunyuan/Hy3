import { z } from 'zod';

const reasoningEffortSchema = z.enum(['no_think', 'low', 'high']);

const positiveIntegerFromEnvironment = (fallback: number) =>
  z
    .string()
    .regex(/^\d+$/, 'must be a positive integer')
    .transform(Number)
    .pipe(z.number().int().positive())
    .optional()
    .default(String(fallback));

const environmentSchema = z.object({
  HY3_API_KEY: z.string().min(1).optional(),
  HY3_BASE_URL: z.string().url().default('http://127.0.0.1:8000/v1'),
  HY3_MODEL: z.string().min(1).max(128).default('hy3'),
  HY3_REASONING_EFFORT: reasoningEffortSchema.default('high'),
  HY3_TIMEOUT_MS: positiveIntegerFromEnvironment(60_000),
  MCPQ_TARGETS_FILE: z.string().min(1).optional(),
});

export type RuntimeConfig = {
  hy3: {
    apiKeyPresent: boolean;
    baseUrl: string;
    model: string;
    reasoningEffort: z.infer<typeof reasoningEffortSchema>;
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
