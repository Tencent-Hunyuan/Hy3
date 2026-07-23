#!/usr/bin/env node

import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';

import { loadRuntimeConfig } from './config.js';
import { createServer } from './server.js';

async function main(): Promise<void> {
  loadRuntimeConfig();
  const server = createServer();
  const transport = new StdioServerTransport();

  const shutdown = async (): Promise<void> => {
    await server.close();
  };

  process.once('SIGINT', () => {
    void shutdown().finally(() => process.exit(0));
  });
  process.once('SIGTERM', () => {
    void shutdown().finally(() => process.exit(0));
  });

  await server.connect(transport);
  console.error('Hy3 MCP Quality Gate running on stdio');
}

main().catch((error: unknown) => {
  const message = error instanceof Error ? error.message : 'unknown startup error';
  console.error(`Hy3 MCP Quality Gate failed: ${message}`);
  process.exitCode = 1;
});
