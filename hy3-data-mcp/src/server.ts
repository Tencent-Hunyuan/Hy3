import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js";
import { Hy3Client, loadConfig } from "./client.js";
import { handleToolCall, TOOL_DEFINITIONS } from "./tools/index.js";

export async function startServer() {
  const config = loadConfig();
  const client = new Hy3Client(config);

  const server = new Server(
    {
      name: "hy3-data-mcp",
      version: "0.1.0",
    },
    {
      capabilities: {
        tools: {},
      },
    }
  );

  server.setRequestHandler(ListToolsRequestSchema, async () => {
    return { tools: TOOL_DEFINITIONS };
  });

  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;
    return handleToolCall(name, args ?? {}, client);
  });

  const transport = new StdioServerTransport();
  await server.connect(transport);
}
