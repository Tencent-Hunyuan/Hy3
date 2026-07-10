import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtemp, mkdir, writeFile, readFile, rm } from "fs/promises";
import { tmpdir } from "os";
import { join } from "path";
import { installMcpConfig } from "../src/cli/config.js";

describe("CLI installer", () => {
  let tempDir: string;

  beforeEach(async () => {
    tempDir = await mkdtemp(join(tmpdir(), "hy3-data-mcp-cli-"));
  });

  afterEach(async () => {
    await rm(tempDir, { recursive: true, force: true });
  });

  it("detects CodeBuddy config in ~/.codebuddy/.mcp.json", async () => {
    const originalUserProfile = process.env.USERPROFILE;
    const originalHome = process.env.HOME;
    process.env.USERPROFILE = tempDir;
    process.env.HOME = tempDir;

    const { detectClients } = await import("../src/cli/detect.js");
    await mkdir(join(tempDir, ".codebuddy"), { recursive: true });
    await writeFile(join(tempDir, ".codebuddy", ".mcp.json"), "{}", "utf-8");

    const clients = await detectClients(tempDir);
    const codebuddy = clients.find((c) => c.id === "codebuddy");
    expect(codebuddy).toBeDefined();
    expect(codebuddy?.configPath).toBe(join(tempDir, ".codebuddy", ".mcp.json"));

    process.env.USERPROFILE = originalUserProfile;
    process.env.HOME = originalHome;
  });

  it("does not pick project .mcp.json for CodeBuddy", async () => {
    const originalUserProfile = process.env.USERPROFILE;
    const originalHome = process.env.HOME;
    process.env.USERPROFILE = tempDir;
    process.env.HOME = tempDir;

    const { detectClients } = await import("../src/cli/detect.js");
    await writeFile(join(tempDir, ".mcp.json"), "{}", "utf-8");

    const clients = await detectClients(tempDir);
    const codebuddy = clients.find((c) => c.id === "codebuddy");
    expect(codebuddy?.configPath).toBe(join(tempDir, ".codebuddy", ".mcp.json"));

    process.env.USERPROFILE = originalUserProfile;
    process.env.HOME = originalHome;
  });

  it("installs MCP config into a client file", async () => {
    const configPath = join(tempDir, "mcp.json");
    await installMcpConfig(configPath, {
      apiKey: "test-key",
      baseURL: "https://tokenhub.tencentmaas.com/v1",
      model: "hy3-preview",
      outputDir: "./hy3-data-output",
    });

    const content = await readFile(configPath, "utf-8");
    const parsed = JSON.parse(content);
    expect(parsed.mcpServers["hy3-data-mcp"]).toBeDefined();
    expect(parsed.mcpServers["hy3-data-mcp"].env.HY3_API_KEY).toBe("test-key");
  });
});
