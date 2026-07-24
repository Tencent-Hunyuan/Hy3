import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';

const sharedExportContract = {
  description:
    'Export selected synthetic records into an inert JSON document.',
  inputSchema: {
    type: 'object' as const,
    properties: {
      record_ids: {
        type: 'array',
        items: { type: 'string' },
        minItems: 1,
        description: 'Synthetic record identifiers to include.',
      },
    },
    required: ['record_ids'],
    additionalProperties: false,
  },
  outputSchema: {
    type: 'object' as const,
    properties: {
      document: { type: 'string' },
    },
    required: ['document'],
  },
  annotations: {
    readOnlyHint: true,
    destructiveHint: false,
    idempotentHint: true,
    openWorldHint: false,
  },
};

const server = new Server(
  { name: 'fixture-compat-breaking', version: '2.0.0' },
  { capabilities: { tools: {} } },
);

server.setRequestHandler(ListToolsRequestSchema, () =>
  Promise.resolve({
    tools: [
      {
        name: 'search_records',
        description:
          'Search a remote tenant index and return a compact match count.',
        inputSchema: {
          type: 'object' as const,
          properties: {
            query: {
              type: 'string',
              minLength: 1,
              maxLength: 50,
              description: 'Search text used against the remote tenant index.',
            },
            mode: {
              type: 'string',
              enum: ['exact'],
              description: 'Matching strategy for the remote search.',
            },
            tenant: {
              type: 'string',
              description: 'Tenant identifier required by the remote index.',
            },
          },
          required: ['query', 'tenant'],
          additionalProperties: false,
        },
        outputSchema: {
          type: 'object' as const,
          properties: {
            count: { type: 'integer', minimum: 0 },
          },
          required: ['count'],
        },
        annotations: {
          readOnlyHint: true,
          destructiveHint: false,
          idempotentHint: true,
          openWorldHint: true,
        },
      },
      {
        name: 'export_records',
        ...sharedExportContract,
      },
      {
        name: 'health_status',
        description:
          'Return synthetic availability metadata for this fixture.',
        inputSchema: {
          type: 'object' as const,
          properties: {},
          additionalProperties: false,
        },
        outputSchema: {
          type: 'object' as const,
          properties: {
            ready: { type: 'boolean' },
          },
          required: ['ready'],
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
