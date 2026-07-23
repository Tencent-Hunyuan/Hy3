import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';

const properties = Object.fromEntries(
  Array.from({ length: 700 }, (_, index) => [
    `field_${index}`,
    {
      type: 'string',
      description: 'Synthetic documented field used for limit testing.',
    },
  ]),
);

const server = new Server(
  { name: 'fixture-oversized-contract', version: '1.0.0' },
  { capabilities: { tools: {} } },
);

server.setRequestHandler(ListToolsRequestSchema, () =>
  Promise.resolve({
    tools: [
      {
        name: 'inspect_large_contract',
        description:
          'Return a synthetic large contract used to verify deterministic audit limits.',
        inputSchema: {
          type: 'object' as const,
          properties,
        },
        outputSchema: {
          type: 'object' as const,
          properties: {
            accepted: { type: 'boolean' },
          },
        },
        annotations: {
          readOnlyHint: true,
          destructiveHint: false,
          idempotentHint: true,
          openWorldHint: false,
        },
      },
    ],
  }),
);

await server.connect(new StdioServerTransport());
