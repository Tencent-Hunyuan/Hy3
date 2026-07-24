import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import type { CallToolResult } from '@modelcontextprotocol/sdk/types.js';

import {
  auditInputSchema,
  auditOutputSchema,
  compareInputSchema,
  compareOutputSchema,
  inspectInputSchema,
  inspectOutputSchema,
  probeInputSchema,
  probeOutputSchema,
  type AuditInput,
  type CompareInput,
  type InspectInput,
  type ProbeInput,
} from '../tool-contracts.js';

export type ToolHandlers = {
  inspect: (input: InspectInput) => Promise<CallToolResult>;
  audit: (input: AuditInput) => Promise<CallToolResult>;
  compare: (input: CompareInput) => Promise<CallToolResult>;
  probes: (input: ProbeInput) => Promise<CallToolResult>;
};

function unavailable(toolName: string): Promise<CallToolResult> {
  return Promise.resolve({
    isError: true,
    content: [
      {
        type: 'text',
        text: `${toolName} is registered but is not available in this implementation stage.`,
      },
    ],
  });
}

export function createDefaultHandlers(): ToolHandlers {
  return {
    inspect: async () => unavailable('mcpq_inspect_server'),
    audit: async () => unavailable('mcpq_audit_contracts'),
    compare: async () => unavailable('mcpq_compare_contracts'),
    probes: async () => unavailable('mcpq_generate_probe_suite'),
  };
}

export function registerTools(server: McpServer, handlers: ToolHandlers): void {
  server.registerTool(
    'mcpq_inspect_server',
    {
      title: 'Inspect MCP Server',
      description:
        'Start a pre-registered local MCP server, negotiate the protocol, list its tools, and return deterministic evidence about lifecycle or contract failures.',
      inputSchema: inspectInputSchema,
      outputSchema: inspectOutputSchema,
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: false,
      },
    },
    handlers.inspect,
  );

  server.registerTool(
    'mcpq_audit_contracts',
    {
      title: 'Audit MCP Tool Contracts',
      description:
        'Audit a pre-registered MCP server with deterministic rules and optional Hy3 semantic review, preserving evidence and separating facts from model judgments.',
      inputSchema: auditInputSchema,
      outputSchema: auditOutputSchema,
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: true,
      },
    },
    handlers.audit,
  );

  server.registerTool(
    'mcpq_compare_contracts',
    {
      title: 'Compare MCP Contracts',
      description:
        'Compare two pre-registered MCP server versions, identify structural compatibility changes, and optionally ask Hy3 to explain semantic migration impact.',
      inputSchema: compareInputSchema,
      outputSchema: compareOutputSchema,
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: true,
      },
    },
    handlers.compare,
  );

  server.registerTool(
    'mcpq_generate_probe_suite',
    {
      title: 'Generate MCP Probe Suite',
      description:
        'Use Hy3 to generate bounded normal, boundary, error, and adversarial test cases for one discovered tool without executing the generated cases.',
      inputSchema: probeInputSchema,
      outputSchema: probeOutputSchema,
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: false,
        openWorldHint: true,
      },
    },
    handlers.probes,
  );
}
