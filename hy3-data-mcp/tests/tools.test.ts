import { describe, it, expect, vi } from "vitest";
import { handleToolCall } from "../src/tools/index.js";
import { Hy3Client } from "../src/client.js";
import { mkdtemp, writeFile } from "fs/promises";
import { tmpdir } from "os";
import { join } from "path";

function createMockClient(response = "mocked response") {
  return {
    chat: vi.fn().mockImplementation(async (_messages, options) => {
      if (options?.onToken) {
        options.onToken(response);
      }
      return response;
    }),
  } as unknown as Hy3Client;
}

describe("handleToolCall", () => {
  it("routes hy3_data_insight and returns text content", async () => {
    const dir = await mkdtemp(join(tmpdir(), "hy3-mcp-"));
    const file = join(dir, "data.csv");
    await writeFile(file, "name,value\nA,10\nB,20\n");

    const client = createMockClient('{"insight": "mock"}');
    const result = await handleToolCall(
      "hy3_data_insight",
      { file_path: file, question: "Summarize", language: "en" },
      client
    );
    expect(result.content).toHaveLength(1);
    expect(result.content[0].type).toBe("text");
    expect(result.content[0].text).toBe('{"insight": "mock"}');
  });

  it("throws on unknown tool", async () => {
    const client = createMockClient();
    await expect(handleToolCall("unknown_tool", {}, client)).rejects.toThrow(
      "Unknown tool: unknown_tool"
    );
  });
});
