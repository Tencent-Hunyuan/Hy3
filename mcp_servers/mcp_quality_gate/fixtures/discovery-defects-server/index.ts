import { createInterface } from 'node:readline';

type JsonRpcRequest = {
  id?: number | string;
  method?: string;
  params?: {
    protocolVersion?: string;
  };
};

function respond(id: number | string, result: unknown): void {
  process.stdout.write(`${JSON.stringify({ jsonrpc: '2.0', id, result })}\n`);
}

const input = createInterface({
  input: process.stdin,
  crlfDelay: Infinity,
});

for await (const line of input) {
  const request = JSON.parse(line) as JsonRpcRequest;
  if (request.id === undefined) {
    continue;
  }
  if (request.method === 'initialize') {
    respond(request.id, {
      protocolVersion: request.params?.protocolVersion ?? '2025-11-25',
      capabilities: { tools: {} },
    });
    continue;
  }
  if (request.method === 'tools/list') {
    if (process.env.FIXTURE_INVALID_LIST === '1') {
      respond(request.id, { unexpected: [] });
      continue;
    }
    respond(request.id, {
      tools: [
        {
          name: 'duplicate_tool',
          description:
            'Return the first synthetic value for duplicate-name testing.',
          inputSchema: {
            type: 'object',
            properties: {
              value: {
                type: 'string',
                description: 'First synthetic value to return.',
              },
            },
          },
          annotations: {
            readOnlyHint: true,
            destructiveHint: false,
            idempotentHint: true,
            openWorldHint: false,
          },
        },
        {
          name: 'duplicate_tool',
          description:
            'Return the second synthetic value for duplicate-name testing.',
          inputSchema: {
            type: 'object',
            properties: {
              value: {
                type: 'string',
                description: 'Second synthetic value to return.',
              },
            },
          },
          annotations: {
            readOnlyHint: true,
            destructiveHint: false,
            idempotentHint: true,
            openWorldHint: false,
          },
        },
        {
          name: 'Invalid Tool',
          description:
            'Return a synthetic value while exposing an invalid tool contract.',
          inputSchema: {},
          annotations: {
            readOnlyHint: true,
            destructiveHint: false,
            idempotentHint: true,
            openWorldHint: false,
          },
        },
      ],
    });
  }
}
