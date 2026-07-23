import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';

import {
  createDefaultHandlers,
  registerTools,
  type ToolHandlers,
} from './tools/register.js';
import { PACKAGE_NAME, PACKAGE_VERSION } from './version.js';

export function createServer(handlers: ToolHandlers = createDefaultHandlers()): McpServer {
  const server = new McpServer(
    {
      name: PACKAGE_NAME,
      version: PACKAGE_VERSION,
    },
    {
      instructions:
        'Select only target IDs configured by the local operator. Inspection is read-only and generated probes are never executed.',
    },
  );

  registerTools(server, handlers);
  return server;
}
