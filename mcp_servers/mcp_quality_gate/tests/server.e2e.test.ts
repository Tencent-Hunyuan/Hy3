import assert from 'node:assert/strict';
import { resolve } from 'node:path';
import { describe, it } from 'node:test';

import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const serverEntry = resolve(process.cwd(), 'dist/src/index.js');

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

  it('returns a controlled error for a later-stage tool', async () => {
    const client = new Client({ name: 'quality-gate-test', version: '0.1.0' });
    const transport = new StdioClientTransport({
      command: process.execPath,
      args: [serverEntry],
      stderr: 'pipe',
    });

    try {
      await client.connect(transport);
      const result = await client.callTool({
        name: 'mcpq_audit_contracts',
        arguments: { target_id: 'fixture-good' },
      });

      assert.equal(result.isError, true);
    } finally {
      await client.close();
    }
  });
});
