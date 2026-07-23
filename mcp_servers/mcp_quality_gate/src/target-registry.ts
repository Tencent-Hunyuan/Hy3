import { readFile, realpath } from 'node:fs/promises';
import { dirname, isAbsolute, relative, resolve } from 'node:path';

import { z } from 'zod';

import { containsCredentialLikeValue } from './security/redaction.js';
import { targetIdSchema } from './tool-contracts.js';

const HARD_LIMITS = {
  startup_timeout_ms: 30_000,
  request_timeout_ms: 30_000,
  total_timeout_ms: 60_000,
  max_stdout_bytes: 8 * 1024 * 1024,
  max_stderr_bytes: 2 * 1024 * 1024,
} as const;

const SECRET_ENVIRONMENT_NAME =
  /(?:^|_)(?:KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|PRIVATE|AUTH)(?:_|$)|^(?:AWS|AZURE|GOOGLE|GITHUB|GH|GPG|HY3|SSH)_/i;

const limitFields = {
  startup_timeout_ms: z.number().int().min(100).max(HARD_LIMITS.startup_timeout_ms),
  request_timeout_ms: z.number().int().min(100).max(HARD_LIMITS.request_timeout_ms),
  total_timeout_ms: z.number().int().min(500).max(HARD_LIMITS.total_timeout_ms),
  max_stdout_bytes: z.number().int().min(1024).max(HARD_LIMITS.max_stdout_bytes),
  max_stderr_bytes: z.number().int().min(1024).max(HARD_LIMITS.max_stderr_bytes),
} as const;

function validateLimitRelationships(
  value: {
    startup_timeout_ms: number;
    request_timeout_ms: number;
    total_timeout_ms: number;
  },
  context: z.RefinementCtx,
): void {
    if (value.total_timeout_ms < value.startup_timeout_ms) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['total_timeout_ms'],
        message: 'total timeout must not be lower than startup timeout',
      });
    }
    if (value.total_timeout_ms < value.request_timeout_ms) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['total_timeout_ms'],
        message: 'total timeout must not be lower than request timeout',
      });
    }
}

const limitsObjectSchema = z.object(limitFields).strict();
const limitsSchema = limitsObjectSchema.superRefine(validateLimitRelationships);

const targetLimitsSchema = limitsObjectSchema.partial();

const targetSchema = z
  .object({
    description: z.string().min(1).max(500),
    command: z.string().min(1).max(1024),
    args: z.array(z.string().max(4096)).max(64).default([]),
    cwd: z.string().min(1).max(4096),
    env: z.record(z.string().max(16_384)).default({}),
    inherit_env: z.array(z.string().min(1).max(256)).max(32).optional(),
    limits: targetLimitsSchema.optional(),
  })
  .strict();

const registrySchema = z
  .object({
    version: z.literal(1),
    allowed_roots: z.array(z.string().min(1)).min(1).max(32),
    defaults: z
      .object({
        ...limitFields,
        inherit_env: z.array(z.string().min(1).max(256)).max(32).default([]),
      })
      .strict()
      .superRefine(validateLimitRelationships),
    targets: z.record(targetIdSchema, targetSchema),
  })
  .strict();

export type TargetLimits = z.infer<typeof limitsObjectSchema>;
type TargetLimitOverrides = {
  [Key in keyof TargetLimits]?: number | undefined;
};

export type ResolvedTarget = {
  id: string;
  description: string;
  command: string;
  args: readonly string[];
  cwd: string;
  environment: NodeJS.ProcessEnv;
  limits: TargetLimits;
};

export class TargetRegistryError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'TargetRegistryError';
  }
}

function within(root: string, candidate: string): boolean {
  const pathFromRoot = relative(root, candidate);
  return (
    pathFromRoot === '' ||
    (!pathFromRoot.startsWith(`..${process.platform === 'win32' ? '\\' : '/'}`) &&
      pathFromRoot !== '..' &&
      !isAbsolute(pathFromRoot))
  );
}

function assertSafeEnvironmentName(name: string): void {
  if (SECRET_ENVIRONMENT_NAME.test(name)) {
    throw new TargetRegistryError(
      `target environment name is denied by policy: ${name}`,
    );
  }
}

function buildEnvironment(
  inheritedNames: readonly string[],
  fixed: Readonly<Record<string, string>>,
  hostEnvironment: NodeJS.ProcessEnv,
): NodeJS.ProcessEnv {
  const environment: NodeJS.ProcessEnv = {};
  for (const name of inheritedNames) {
    assertSafeEnvironmentName(name);
    const value = hostEnvironment[name];
    if (value !== undefined) {
      environment[name] = value;
    }
  }
  for (const [name, value] of Object.entries(fixed)) {
    assertSafeEnvironmentName(name);
    if (containsCredentialLikeValue(value)) {
      throw new TargetRegistryError(
        `target environment value is denied by policy: ${name}`,
      );
    }
    environment[name] = value;
  }
  return environment;
}

function mergeLimits(
  defaults: TargetLimits,
  override: TargetLimitOverrides | undefined,
): TargetLimits {
  if (override !== undefined) {
    for (const [name, value] of Object.entries(override)) {
      if (value === undefined) {
        continue;
      }
      const key = name as keyof TargetLimits;
      if (value > defaults[key]) {
        throw new TargetRegistryError(
          `target limit ${name} must not exceed its registry default`,
        );
      }
    }
  }
  return limitsSchema.parse({ ...defaults, ...override });
}

function defaultLimitsFrom(
  defaults: z.infer<typeof registrySchema>['defaults'],
): TargetLimits {
  return {
    startup_timeout_ms: defaults.startup_timeout_ms,
    request_timeout_ms: defaults.request_timeout_ms,
    total_timeout_ms: defaults.total_timeout_ms,
    max_stdout_bytes: defaults.max_stdout_bytes,
    max_stderr_bytes: defaults.max_stderr_bytes,
  };
}

export class TargetRegistry {
  readonly #targets: ReadonlyMap<string, ResolvedTarget>;

  private constructor(targets: ReadonlyMap<string, ResolvedTarget>) {
    this.#targets = targets;
  }

  static empty(): TargetRegistry {
    return new TargetRegistry(new Map());
  }

  static async load(
    registryPath: string,
    hostEnvironment: NodeJS.ProcessEnv = process.env,
  ): Promise<TargetRegistry> {
    let canonicalRegistryPath: string;
    try {
      canonicalRegistryPath = await realpath(registryPath);
    } catch {
      throw new TargetRegistryError('target registry does not exist or is unreadable');
    }

    let raw: unknown;
    try {
      raw = JSON.parse(await readFile(canonicalRegistryPath, 'utf8')) as unknown;
    } catch {
      throw new TargetRegistryError('target registry is not valid UTF-8 JSON');
    }

    const parsedResult = registrySchema.safeParse(raw);
    if (!parsedResult.success) {
      throw new TargetRegistryError(
        `target registry validation failed: ${parsedResult.error.issues[0]?.message ?? 'unknown error'}`,
      );
    }

    const parsed = parsedResult.data;
    const registryDirectory = dirname(canonicalRegistryPath);
    const registryDefaultLimits = defaultLimitsFrom(parsed.defaults);
    let roots: string[];
    try {
      roots = await Promise.all(
        parsed.allowed_roots.map(async (root) =>
          realpath(resolve(registryDirectory, root)),
        ),
      );
    } catch {
      throw new TargetRegistryError('an allowed root does not exist or is unreadable');
    }
    const targets = new Map<string, ResolvedTarget>();

    for (const [id, target] of Object.entries(parsed.targets)) {
      let cwd: string;
      try {
        cwd = await realpath(resolve(registryDirectory, target.cwd));
      } catch {
        throw new TargetRegistryError(`target ${id} cwd does not exist`);
      }
      if (!roots.some((root) => within(root, cwd))) {
        throw new TargetRegistryError(`target ${id} cwd is outside allowed roots`);
      }

      const inheritedNames = target.inherit_env ?? parsed.defaults.inherit_env;
      const limits = mergeLimits(registryDefaultLimits, target.limits);
      targets.set(id, {
        id,
        description: target.description,
        command: target.command,
        args: [...target.args],
        cwd,
        environment: buildEnvironment(inheritedNames, target.env, hostEnvironment),
        limits,
      });
    }

    return new TargetRegistry(targets);
  }

  get(targetId: string): ResolvedTarget {
    const target = this.#targets.get(targetId);
    if (target === undefined) {
      throw new TargetRegistryError(`unknown target_id: ${targetId}`);
    }
    return target;
  }

  listIds(): string[] {
    return [...this.#targets.keys()].sort();
  }
}
