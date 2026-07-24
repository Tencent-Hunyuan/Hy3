import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';

const server = new McpServer({ name: 'fixture-good', version: '1.0.0' });

server.registerTool(
  'fixture_echo',
  {
    description: 'Return the provided synthetic text unchanged for protocol tests.',
    inputSchema: z.object({
      text: z.string().max(1000).describe('Synthetic text to return.'),
    }),
    outputSchema: z.object({ echoed: z.string() }),
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: false,
    },
  },
  async ({ text }) => {
    const output = { echoed: text };
    return {
      content: [{ type: 'text', text }],
      structuredContent: output,
    };
  },
);

server.registerTool(
  'fixture_sum',
  {
    description: 'Add two finite synthetic numbers for protocol discovery tests.',
    inputSchema: z.object({
      left: z.number().finite().describe('First number.'),
      right: z.number().finite().describe('Second number.'),
    }),
    outputSchema: z.object({ sum: z.number() }),
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: false,
    },
  },
  async ({ left, right }) => {
    const output = { sum: left + right };
    return {
      content: [{ type: 'text', text: String(output.sum) }],
      structuredContent: output,
    };
  },
);

await server.connect(new StdioServerTransport());
