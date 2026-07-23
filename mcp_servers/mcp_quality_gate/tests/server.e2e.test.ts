import assert from 'node:assert/strict';
import { resolve } from 'node:path';
import { describe, it } from 'node:test';

import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const serverEntry = resolve(process.cwd(), 'dist/src/index.js');
const exampleRegistry = resolve(process.cwd(), 'examples/targets.example.json');

describe('stdio server', () => {
  it('initializes and exposes exactly the four planned tools', async () => {
    const client = new Client({ name: 'quality-gate-test', version: '0.1.0' });
    const transport = new StdioClientTransport({
      command: process.execPath,
      args: [serverEntry],
      stderr: 'pipe',
    });

    try {
      await client.connect(transport);
      const { tools } = await client.listTools();

      assert.deepEqual(
        tools.map((tool) => tool.name).sort(),
        [
          'mcpq_audit_contracts',
          'mcpq_compare_contracts',
          'mcpq_generate_probe_suite',
          'mcpq_inspect_server',
        ],
      );
      for (const tool of tools) {
        assert.ok((tool.description?.length ?? 0) > 60);
        assert.equal(tool.inputSchema.type, 'object');
        assert.equal(tool.outputSchema?.type, 'object');
        assert.equal(tool.annotations?.readOnlyHint, true);
      }
    } finally {
      await client.close();
    }
  });

  it('returns a controlled error for a later-stage comparison tool', async () => {
    const client = new Client({ name: 'quality-gate-test', version: '0.1.0' });
    const transport = new StdioClientTransport({
      command: process.execPath,
      args: [serverEntry],
      stderr: 'pipe',
    });

    try {
      await client.connect(transport);
      const result = await client.callTool({
        name: 'mcpq_compare_contracts',
        arguments: {
          baseline_target_id: 'fixture-good',
          current_target_id: 'fixture-current',
        },
      });

      assert.equal(result.isError, true);
    } finally {
      await client.close();
    }
  });

  it('calls the working inspector through the complete MCP stdio chain', async () => {
    const client = new Client({ name: 'quality-gate-test', version: '0.1.0' });
    const transport = new StdioClientTransport({
      command: process.execPath,
      args: [serverEntry],
      env: { MCPQ_TARGETS_FILE: exampleRegistry },
      stderr: 'pipe',
    });

    try {
      await client.connect(transport);
      const good = await client.callTool({
        name: 'mcpq_inspect_server',
        arguments: { target_id: 'fixture-good' },
      });
      const polluted = await client.callTool({
        name: 'mcpq_inspect_server',
        arguments: { target_id: 'fixture-stdout-pollution' },
      });
      const goodContent = good.structuredContent as
        | { status: string; tools: Array<{ name: string }> }
        | undefined;
      const pollutedContent = polluted.structuredContent as
        | { status: string; findings: Array<{ rule_id: string }> }
        | undefined;

      assert.equal(good.isError, undefined);
      assert.ok(goodContent);
      assert.equal(goodContent.status, 'pass');
      assert.deepEqual(
        goodContent.tools.map((tool) => tool.name),
        ['fixture_echo', 'fixture_sum'],
      );
      assert.ok(pollutedContent);
      assert.equal(pollutedContent.status, 'fail');
      assert.ok(
        pollutedContent.findings.some((item) => item.rule_id === 'PROTO-002'),
      );
    } finally {
      await client.close();
    }
  });

  it('calls the deterministic audit through the complete MCP stdio chain', async () => {
    const client = new Client({ name: 'quality-gate-test', version: '0.1.0' });
    const transport = new StdioClientTransport({
      command: process.execPath,
      args: [serverEntry],
      env: { MCPQ_TARGETS_FILE: exampleRegistry },
      stderr: 'pipe',
    });

    try {
      await client.connect(transport);
      const good = await client.callTool({
        name: 'mcpq_audit_contracts',
        arguments: {
          target_id: 'fixture-good',
          include_hy3: false,
        },
      });
      const bad = await client.callTool({
        name: 'mcpq_audit_contracts',
        arguments: {
          target_id: 'fixture-audit-bad',
          include_hy3: false,
        },
      });
      const goodContent = good.structuredContent as
        | {
            status: string;
            scorecard: { overall: number };
            catalog_version: string;
          }
        | undefined;
      const badContent = bad.structuredContent as
        | {
            status: string;
            scorecard: { overall: number };
            deterministic_findings: Array<{ rule_id: string }>;
          }
        | undefined;

      assert.equal(good.isError, undefined);
      assert.ok(goodContent);
      assert.equal(goodContent.status, 'pass');
      assert.equal(goodContent.scorecard.overall, 100);
      assert.equal(goodContent.catalog_version, '1.0.0');
      assert.equal(bad.isError, undefined);
      assert.ok(badContent);
      assert.equal(badContent.status, 'fail');
      assert.ok(badContent.scorecard.overall < 100);
      assert.ok(
        badContent.deterministic_findings.some(
          (finding) => finding.rule_id === 'SAFETY-001',
        ),
      );
    } finally {
      await client.close();
    }
  });
});
