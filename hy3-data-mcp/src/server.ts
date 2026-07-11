import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { Hy3Client, loadConfig } from "./client.js";
import { InMemoryTaskMessageQueue } from "./tasks/queue.js";
import { InMemoryTaskStore } from "./tasks/store.js";
import { registerTools } from "./tools/index.js";

export async function startServer() {
  const config = loadConfig();
  const client = new Hy3Client(config);

  const taskStore = new InMemoryTaskStore();
  const taskMessageQueue = new InMemoryTaskMessageQueue();

  const server = new McpServer(
    {
      name: "hy3-data-mcp",
      version: "0.3.1",
    },
    {
      capabilities: {
        tools: {},
        tasks: {
          list: {},
          cancel: {},
          requests: {
            tools: {
              call: {},
            },
          },
        },
      },
      taskStore,
      taskMessageQueue,
    }
  );

  registerTools(server, client);

  const transport = new StdioServerTransport();
  await server.connect(transport);
}
