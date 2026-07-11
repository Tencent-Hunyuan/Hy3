import { describe, it, expect, vi } from "vitest";
import { handleToolCall } from "../src/tools/index.js";
import { Hy3Client } from "../src/client.js";
import { mkdtemp, writeFile, readFile, rm } from "fs/promises";
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
  it("routes hy3_analyze and returns text content", async () => {
    const dir = await mkdtemp(join(tmpdir(), "hy3-mcp-"));
    const file = join(dir, "data.csv");
    await writeFile(file, "name,value\nA,10\nB,20\n");

    const client = createMockClient('{"insight": "mock"}');
    const result = await handleToolCall(
      "hy3_analyze",
      { data_file_path: file, question: "Summarize", language: "en" },
      client
    );
    expect(result.content).toHaveLength(1);
    expect(result.content[0].type).toBe("text");
    expect(result.content[0].text).toBe('{"insight": "mock"}');
  });

  it("writes decoded HTML directly when hy3_analyze returns entity-encoded HTML", async () => {
    const dir = await mkdtemp(join(tmpdir(), "hy3-mcp-"));
    const file = join(dir, "data.csv");
    await writeFile(file, "name,value\nA,10\nB,20\n");
    process.env.HY3_OUTPUT_DIR = dir;

    const encoded =
      "&lt;!DOCTYPE html&gt;&lt;html&gt;&lt;body&gt;&lt;h1&gt;Report&lt;/h1&gt;&lt;p&gt;OK&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;";
    const client = createMockClient(encoded);
    const result = await handleToolCall(
      "hy3_analyze",
      { data_file_path: file, question: "Summarize", output_format: "html", language: "en" },
      client
    );

    const match = result.content[0].text.match(/File path: (.+\.html)/);
    expect(match).toBeTruthy();
    const htmlPath = match![1];
    const html = await readFile(htmlPath, "utf-8");
    expect(html).toContain("<!DOCTYPE html>");
    expect(html).toContain("<h1>Report</h1>");
    expect(html).not.toContain("&lt;!DOCTYPE html&gt;");

    delete process.env.HY3_OUTPUT_DIR;
    await rm(dir, { recursive: true, force: true });
  });

  it("throws on unknown tool", async () => {
    const client = createMockClient();
    await expect(handleToolCall("unknown_tool", {}, client)).rejects.toThrow(
      "Unknown tool: unknown_tool"
    );
  });
});
