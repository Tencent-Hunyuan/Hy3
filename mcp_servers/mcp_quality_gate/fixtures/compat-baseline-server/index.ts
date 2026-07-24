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
  { name: 'fixture-compat-baseline', version: '1.0.0' },
  { capabilities: { tools: {} } },
);

server.setRequestHandler(ListToolsRequestSchema, () =>
  Promise.resolve({
    tools: [
      {
        name: 'search_records',
        description:
          'Search local synthetic records and return matching summaries without modifying data.',
        inputSchema: {
          type: 'object' as const,
          properties: {
            query: {
              type: 'string',
              minLength: 1,
              maxLength: 100,
              description: 'Search text used to match synthetic records.',
            },
            mode: {
              type: 'string',
              enum: ['exact', 'fuzzy'],
              description: 'Matching strategy for the local search.',
            },
          },
          required: ['query'],
          additionalProperties: false,
        },
        outputSchema: {
          type: 'object' as const,
          properties: {
            records: {
              type: 'array',
              items: {
                type: 'object',
                properties: {
                  id: { type: 'string' },
                  summary: { type: 'string' },
                },
                required: ['id', 'summary'],
              },
            },
          },
          required: ['records'],
        },
        annotations: {
          readOnlyHint: true,
          destructiveHint: false,
          idempotentHint: true,
          openWorldHint: false,
        },
      },
      {
        name: 'legacy_lookup',
        description:
          'Look up one synthetic record by its stable local identifier.',
        inputSchema: {
          type: 'object' as const,
          properties: {
            record_id: {
              type: 'string',
              description: 'Stable synthetic record identifier.',
            },
          },
          required: ['record_id'],
          additionalProperties: false,
        },
        outputSchema: {
          type: 'object' as const,
          properties: {
            found: { type: 'boolean' },
          },
          required: ['found'],
        },
        annotations: {
          readOnlyHint: true,
          destructiveHint: false,
          idempotentHint: true,
          openWorldHint: false,
        },
      },
      {
        name: 'legacy_export',
        ...sharedExportContract,
      },
    ],
  }),
);

await server.connect(new StdioServerTransport());
