import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { fileURLToPath } from 'node:url';
import { delimiter, dirname, resolve } from 'node:path';

const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const serverEntry = resolve(packageRoot, 'dist/src/index.js');
const targetsFile = resolve(packageRoot, 'examples/targets.example.json');
const runtimePath = [dirname(process.execPath), process.env.PATH]
  .filter(Boolean)
  .join(delimiter);
const client = new Client({
  name: 'hy3-mcp-quality-gate-demo',
  version: '0.1.0',
});
const transport = new StdioClientTransport({
  command: process.execPath,
  args: [serverEntry],
  env: {
    MCPQ_TARGETS_FILE: targetsFile,
    PATH: runtimePath,
  },
  stderr: 'pipe',
});

function structured(result, label) {
  if (
    result.isError === true ||
    result.structuredContent === undefined ||
    result.structuredContent === null ||
    typeof result.structuredContent !== 'object'
  ) {
    throw new Error(`${label} did not return structured content`);
  }
  return result.structuredContent;
}

try {
  await client.connect(transport);
  const { tools } = await client.listTools();
  const inspection = structured(
    await client.callTool({
      name: 'mcpq_inspect_server',
      arguments: {
        target_id: 'fixture-good',
        include_schemas: false,
      },
    }),
    'inspection',
  );
  const audit = structured(
    await client.callTool({
      name: 'mcpq_audit_contracts',
      arguments: {
        target_id: 'fixture-audit-bad',
        include_hy3: false,
      },
    }),
    'audit',
  );
  const comparison = structured(
    await client.callTool({
      name: 'mcpq_compare_contracts',
      arguments: {
        baseline_target_id: 'fixture-compat-baseline',
        current_target_id: 'fixture-compat-breaking',
        include_non_breaking: true,
        include_hy3: false,
      },
    }),
    'comparison',
  );

  process.stdout.write(
    `${JSON.stringify(
      {
        server: 'hy3-mcp-quality-gate',
        discovered_tools: tools.map((tool) => tool.name).sort(),
        inspect: {
          status: inspection.status,
          target_id: inspection.target_id,
          tool_names: Array.isArray(inspection.tools)
            ? inspection.tools.map((tool) => tool.name)
            : [],
        },
        audit: {
          status: audit.status,
          target_id: audit.target_id,
          overall_score: audit.scorecard?.overall,
          rule_ids: Array.isArray(audit.deterministic_findings)
            ? audit.deterministic_findings.map((finding) => finding.rule_id)
            : [],
        },
        compare: {
          status: comparison.status,
          change_count: Array.isArray(comparison.changes)
            ? comparison.changes.length
            : 0,
          rule_ids: Array.isArray(comparison.findings)
            ? [
                ...new Set(
                  comparison.findings.map((finding) => finding.rule_id),
                ),
              ]
            : [],
        },
        generated_probes_executed: false,
      },
      null,
      2,
    )}\n`,
  );
} finally {
  await client.close();
}
