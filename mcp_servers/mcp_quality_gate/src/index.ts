#!/usr/bin/env node

import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';

import { loadRuntimeConfig } from './config.js';
import { Hy3ChatClient } from './hy3/client.js';
import { Hy3MigrationReviewer } from './hy3/migration-reviewer.js';
import { Hy3ProbeGenerator } from './hy3/probe-generator.js';
import { Hy3SemanticReviewer } from './hy3/reviewer.js';
import { createServer } from './server.js';
import { TargetRegistry } from './target-registry.js';
import { createToolHandlers } from './tools/inspection-handler.js';

async function main(): Promise<void> {
  const config = loadRuntimeConfig();
  const registry =
    config.targetsFile === undefined
      ? TargetRegistry.empty()
      : await TargetRegistry.load(config.targetsFile);
  const apiKey = process.env.HY3_API_KEY;
  const dependencies =
    config.hy3.apiKeyPresent && apiKey !== undefined
      ? (() => {
          const client = new Hy3ChatClient({
            apiKey,
            baseUrl: config.hy3.baseUrl,
            model: config.hy3.model,
            timeoutMs: config.hy3.timeoutMs,
          });
          return {
            semanticReviewer: new Hy3SemanticReviewer(
              client,
              config.hy3.reasoningEffort,
            ),
            migrationReviewer: new Hy3MigrationReviewer(
              client,
              config.hy3.reasoningEffort,
            ),
            probeGenerator: new Hy3ProbeGenerator(
              client,
              config.hy3.reasoningEffort,
            ),
          };
        })()
      : {};
  const server = createServer(
    createToolHandlers(registry, dependencies),
  );
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
  void error;
  console.error('Hy3 MCP Quality Gate failed during startup');
  process.exitCode = 1;
});
