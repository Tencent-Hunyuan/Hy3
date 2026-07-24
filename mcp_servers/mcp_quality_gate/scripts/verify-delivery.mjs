import assert from 'node:assert/strict';
import { access, readFile } from 'node:fs/promises';
import { delimiter, dirname, isAbsolute, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const packageRoot = resolve(fileURLToPath(new URL('..', import.meta.url)));
const repositoryRoot = resolve(packageRoot, '../..');
const runtimeRootArgumentIndex = process.argv.indexOf('--runtime-root');
const runtimeRoot =
  runtimeRootArgumentIndex === -1
    ? packageRoot
    : resolve(process.argv[runtimeRootArgumentIndex + 1] ?? '');
const runtimePath = [dirname(process.execPath), process.env.PATH]
  .filter(Boolean)
  .join(delimiter);
const expectedServer = {
  command: 'node',
  args: [
    'mcp_servers/mcp_quality_gate/dist/src/index.js',
  ],
  targetsFile:
    'mcp_servers/mcp_quality_gate/examples/targets.example.json',
};
const credentialPattern =
  /(?:sk-[A-Za-z0-9]{12,}|gh[pousr]_[A-Za-z0-9]{20,}|BEGIN [A-Z ]*PRIVATE KEY|api[_-]?key["']?\s*[:=]\s*["'][^"'$]{8,})/i;
const personalPathPattern =
  /(?:\/Users\/(?!example(?:\/|$))[^/\s"']+|\/home\/(?!example(?:\/|$))[^/\s"']+|[A-Z]:\\Users\\(?!example(?:\\|$))[^\\\s"']+)/;

async function readJson(path) {
  return JSON.parse(await readFile(path, 'utf8'));
}

function validateClientConfig(path, config, requireType) {
  const server = config.mcpServers?.['hy3-mcp-quality-gate'];
  assert.ok(server, `${path} must declare hy3-mcp-quality-gate`);
  assert.equal(server.command, expectedServer.command);
  assert.deepEqual(server.args, expectedServer.args);
  assert.equal(
    server.env?.MCPQ_TARGETS_FILE,
    expectedServer.targetsFile,
  );
  if (requireType) {
    assert.equal(server.type, 'stdio');
  }
  assert.equal(
    isAbsolute(server.args[0]),
    false,
    `${path} must not contain a personal absolute package path`,
  );
}

const packageJsonPath = resolve(packageRoot, 'package.json');
const cursorConfigPath = resolve(repositoryRoot, '.cursor/mcp.json');
const codeBuddyConfigPath = resolve(repositoryRoot, '.mcp.json');
const packageJsonText = await readFile(packageJsonPath, 'utf8');
const cursorConfigText = await readFile(cursorConfigPath, 'utf8');
const codeBuddyConfigText = await readFile(codeBuddyConfigPath, 'utf8');
const packageJson = JSON.parse(packageJsonText);
const runtimePackageJson = await readJson(resolve(runtimeRoot, 'package.json'));

assert.ok(packageJson.files.includes('README_CN.md'));
assert.ok(packageJson.files.includes('assets'));
assert.ok(packageJson.files.includes('docs'));
assert.equal(runtimePackageJson.name, packageJson.name);
assert.equal(runtimePackageJson.version, packageJson.version);
await access(resolve(runtimeRoot, runtimePackageJson.bin['hy3-mcp-quality-gate']));
validateClientConfig(
  '.cursor/mcp.json',
  JSON.parse(cursorConfigText),
  false,
);
validateClientConfig('.mcp.json', JSON.parse(codeBuddyConfigText), true);

for (const [path, text] of [
  ['package.json', packageJsonText],
  ['.cursor/mcp.json', cursorConfigText],
  ['.mcp.json', codeBuddyConfigText],
]) {
  assert.equal(credentialPattern.test(text), false, `${path} contains a credential`);
  assert.equal(
    personalPathPattern.test(text),
    false,
    `${path} contains a personal path`,
  );
}

const client = new Client({
  name: 'hy3-mcp-quality-gate-delivery-verifier',
  version: packageJson.version,
});
const transport = new StdioClientTransport({
  command: process.execPath,
  args: [resolve(runtimeRoot, 'dist/src/index.js')],
  env: {
    MCPQ_TARGETS_FILE: resolve(
      runtimeRoot,
      'examples/targets.example.json',
    ),
    PATH: runtimePath,
  },
  stderr: 'pipe',
});

try {
  await client.connect(transport);
  const { tools } = await client.listTools();
  const toolNames = tools.map((tool) => tool.name).sort();
  assert.deepEqual(toolNames, [
    'mcpq_audit_contracts',
    'mcpq_compare_contracts',
    'mcpq_generate_probe_suite',
    'mcpq_inspect_server',
  ]);
  const comparison = tools.find(
    (tool) => tool.name === 'mcpq_compare_contracts',
  );
  assert.ok(comparison?.inputSchema.properties);
  assert.ok('baseline_target_id' in comparison.inputSchema.properties);
  assert.ok('current_target_id' in comparison.inputSchema.properties);

  const result = await client.callTool({
    name: 'mcpq_inspect_server',
    arguments: {
      target_id: 'fixture-good',
      include_schemas: false,
    },
  });
  assert.notEqual(result.isError, true);
  const structured = result.structuredContent;
  assert.ok(structured && typeof structured === 'object');
  assert.equal(structured.status, 'pass');

  process.stdout.write(
    `${JSON.stringify(
      {
        status: 'pass',
        package_version: packageJson.version,
        runtime: runtimeRoot === packageRoot ? 'source' : 'clean-install',
        project_configs: ['.cursor/mcp.json', '.mcp.json'],
        discovered_tools: toolNames,
        fixture_call: {
          tool: 'mcpq_inspect_server',
          target_id: 'fixture-good',
          status: structured.status,
        },
        secrets_or_personal_paths_found: false,
      },
      null,
      2,
    )}\n`,
  );
} finally {
  await client.close();
}
