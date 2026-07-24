import { mkdtemp, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

type TargetDefinition = {
  description?: string;
  command?: string;
  fixture: string;
  env?: Record<string, string>;
  limits?: Record<string, number>;
};

export async function writeTestRegistry(
  packageRoot: string,
  definitions: Record<string, TargetDefinition>,
): Promise<{ directory: string; path: string }> {
  const directory = await mkdtemp(join(tmpdir(), 'hy3-mcpq-test-'));
  const targets = Object.fromEntries(
    Object.entries(definitions).map(([id, definition]) => [
      id,
      {
        description: definition.description ?? `Synthetic ${id} fixture.`,
        command: definition.command ?? process.execPath,
        args: [`dist/fixtures/${definition.fixture}/index.js`],
        cwd: packageRoot,
        env: definition.env ?? {},
        ...(definition.limits === undefined ? {} : { limits: definition.limits }),
      },
    ]),
  );
  const path = join(directory, 'targets.json');
  await writeFile(
    path,
    JSON.stringify(
      {
        version: 1,
        allowed_roots: [packageRoot],
        defaults: {
          startup_timeout_ms: 1000,
          request_timeout_ms: 1000,
          total_timeout_ms: 3000,
          max_stdout_bytes: 262144,
          max_stderr_bytes: 65536,
          inherit_env: [],
        },
        targets,
      },
      null,
      2,
    ),
    'utf8',
  );
  return { directory, path };
}
