import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtemp, mkdir, writeFile, readFile, rm } from "fs/promises";
import { tmpdir } from "os";
import { join } from "path";
import { detectClients } from "../src/cli/detect.js";
import { installMcpConfig } from "../src/cli/config.js";

describe("CLI installer", () => {
  let tempDir: string;

  beforeEach(async () => {
    tempDir = await mkdtemp(join(tmpdir(), "hy3-data-mcp-cli-"));
  });

  afterEach(async () => {
    await rm(tempDir, { recursive: true, force: true });
  });

  it("detects CodeBuddy config in project", async () => {
    await mkdir(join(tempDir, ".codebuddy"), { recursive: true });
    await writeFile(join(tempDir, ".codebuddy", "mcp.json"), "{}", "utf-8");
    const clients = await detectClients(tempDir);
    const codebuddy = clients.find((c) => c.id === "codebuddy");
    expect(codebuddy).toBeDefined();
    expect(codebuddy?.configPath).toContain(".codebuddy");
  });

  it("installs MCP config into a client file", async () => {
    const configPath = join(tempDir, "mcp.json");
    await installMcpConfig(configPath, {
      apiKey: "test-key",
      baseURL: "https://tokenhub.tencentmaas.com/v1",
      model: "hy3-preview",
      outputDir: "./hy3-mcp-output",
    });

    const content = await readFile(configPath, "utf-8");
    const parsed = JSON.parse(content);
    expect(parsed.mcpServers["hy3-data-mcp"]).toBeDefined();
    expect(parsed.mcpServers["hy3-data-mcp"].env.HY3_API_KEY).toBe("test-key");
  });
});
