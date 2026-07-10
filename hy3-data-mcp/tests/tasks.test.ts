import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { writeFile, mkdir, rm } from "fs/promises";
import { join } from "path";
import { tmpdir } from "os";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { CallToolResultSchema } from "@modelcontextprotocol/sdk/types.js";
import { loadConfig, Hy3Client } from "../src/client.js";
import { InMemoryTaskMessageQueue } from "../src/tasks/queue.js";
import { InMemoryTaskStore } from "../src/tasks/store.js";
import { registerTools } from "../src/tools/index.js";

function createMockStream(text: string) {
  async function* stream() {
    yield { choices: [{ delta: { content: `  ${text}  ` } }] };
  }
  return stream();
}

vi.mock("openai", () => {
  return {
    default: class MockOpenAI {
      chat = {
        completions: {
          create: vi.fn().mockImplementation((_params, _options) => {
            if (_params.stream) {
              return createMockStream("mocked hy3 response");
            }
            return Promise.resolve({
              choices: [{ message: { content: "  mocked hy3 response  " } }],
            });
          }),
        },
      };
    },
  };
});

describe("MCP Task/Stream async execution", () => {
  let tmpDir: string;
  let server: McpServer;
  let client: Client;
  const originalKey = process.env.HY3_API_KEY;

  beforeEach(async () => {
    process.env.HY3_API_KEY = "test-key";
    tmpDir = join(tmpdir(), `hy3-task-test-${Date.now()}`);
    await mkdir(tmpDir, { recursive: true });

    const csvPath = join(tmpDir, "data.csv");
    await writeFile(csvPath, "name,value\nA,10\nB,20\n");

    const config = loadConfig();
    const hy3Client = new Hy3Client(config);

    const taskStore = new InMemoryTaskStore();
    const taskMessageQueue = new InMemoryTaskMessageQueue();

    server = new McpServer(
      { name: "hy3-data-mcp", version: "0.1.0" },
      {
        capabilities: {
          tools: {},
          tasks: {
            list: {},
            cancel: {},
            requests: { tools: { call: {} } },
          },
        },
        taskStore,
        taskMessageQueue,
      }
    );

    registerTools(server, hy3Client);

    const [serverTransport, clientTransport] = InMemoryTransport.createLinkedPair();

    client = new Client(
      { name: "test-client", version: "0.1.0" },
      {
        capabilities: {
          tasks: {
            list: {},
            cancel: {},
            requests: { tools: { call: {} } },
          },
        },
      }
    );

    await Promise.all([
      server.connect(serverTransport),
      client.connect(clientTransport),
    ]);
  });

  afterEach(async () => {
    process.env.HY3_API_KEY = originalKey;
    await client.close();
    await server.close();
    await rm(tmpDir, { recursive: true, force: true });
  });

  it("returns taskId and eventually result via task stream", async () => {
    const csvPath = join(tmpDir, "data.csv");
    const stream = client.experimental.tasks.callToolStream(
      {
        name: "hy3_analyze",
        arguments: { data_file_path: csvPath, question: "Summarize" },
      },
      CallToolResultSchema,
      { task: { ttl: 60_000, pollInterval: 500 } }
    );

    const messages: Array<{ type: string; task?: { taskId?: string; status?: string }; result?: unknown }> = [];
    for await (const message of stream) {
      messages.push(message);
      if (message.type === "result" || message.type === "error") break;
    }

    const created = messages.find((m) => m.type === "taskCreated");
    expect(created?.task?.taskId).toBeDefined();

    const completed = messages.find((m) => m.type === "taskStatus" && m.task?.status === "completed");
    expect(completed).toBeDefined();

    const resultMsg = messages.find((m) => m.type === "result");
    expect(resultMsg).toBeDefined();
    expect(resultMsg?.result).toEqual(
      expect.objectContaining({
        content: expect.arrayContaining([
          expect.objectContaining({ type: "text", text: "mocked hy3 response" }),
        ]),
      })
    );
  });

  it("supports synchronous clients with automatic polling", async () => {
    const csvPath = join(tmpDir, "data.csv");
    const result = await client.callTool(
      {
        name: "hy3_analyze",
        arguments: { data_file_path: csvPath, question: "Summarize" },
      },
      CallToolResultSchema
    );

    expect(result.content).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ type: "text", text: "mocked hy3 response" }),
      ])
    );
  });
});
