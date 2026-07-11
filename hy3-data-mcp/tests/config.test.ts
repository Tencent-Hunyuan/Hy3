import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtemp, rm, readFile } from "fs/promises";
import { tmpdir } from "os";
import { join } from "path";
import {
  buildStandardMcpEntry,
  buildOpenCodeMcpEntry,
  buildContinueMcpEntry,
  buildVsCodeMcpEntry,
  installMcpConfig,
} from "../src/cli/config.js";

const baseConfig = {
  apiKey: "test-key",
  baseURL: "https://tokenhub.tencentmaas.com/v1",
  model: "hy3-preview",
  outputDir: "./hy3-data-output",
};

describe("MCP entry builders", () => {
  it("builds a standard stdio entry", () => {
    const entry = buildStandardMcpEntry(baseConfig);
    expect(entry.type).toBe("stdio");
    expect(entry.command).toBe("node");
    expect(entry.args).toHaveLength(1);
    expect(entry.args[0]).toContain("dist");
    expect(entry.env).toMatchObject({ HY3_API_KEY: "test-key" });
  });

  it("builds an OpenCode entry", () => {
    const entry = buildOpenCodeMcpEntry(baseConfig);
    expect(entry.type).toBe("local");
    expect(entry.command[0]).toBe("node");
    expect(entry.command[1]).toContain("dist");
    expect(entry.enabled).toBe(true);
    expect(entry.environment).toMatchObject({ HY3_API_KEY: "test-key" });
  });

  it("builds a Continue entry with a name", () => {
    const entry = buildContinueMcpEntry(baseConfig);
    expect(entry.name).toBe("hy3-data-mcp");
    expect(entry.type).toBe("stdio");
  });

  it("builds a VS Code entry", () => {
    const entry = buildVsCodeMcpEntry(baseConfig);
    expect(entry.type).toBe("stdio");
    expect(entry.env).toMatchObject({ HY3_MODEL: "hy3-preview" });
  });
});

describe("installMcpConfig", () => {
  let tempDir: string;

  beforeEach(async () => {
    tempDir = await mkdtemp(join(tmpdir(), "hy3-config-"));
  });

  afterEach(async () => {
    await rm(tempDir, { recursive: true, force: true });
  });

  it("writes a standard mcp.json", async () => {
    const path = join(tempDir, "mcp.json");
    await installMcpConfig(path, baseConfig);
    const content = JSON.parse(await readFile(path, "utf-8"));
    expect(content.mcpServers["hy3-data-mcp"]).toMatchObject({ type: "stdio" });
  });

  it("writes an OpenCode config with nested mcp key", async () => {
    const path = join(tempDir, "opencode.json");
    await installMcpConfig(path, baseConfig);
    const content = JSON.parse(await readFile(path, "utf-8"));
    expect(content.mcp["hy3-data-mcp"].type).toBe("local");
    expect(content.mcp["hy3-data-mcp"].enabled).toBe(true);
  });

  it("writes a Codex TOML config", async () => {
    const path = join(tempDir, ".codex", "config.toml");
    await installMcpConfig(path, baseConfig);
    const content = await readFile(path, "utf-8");
    expect(content).toContain("[mcp_servers.hy3-data-mcp]");
    expect(content).toContain('command = "node"');
    expect(content).toContain("HY3_API_KEY");
  });

  it("writes a VS Code workspace config with servers key", async () => {
    const path = join(tempDir, ".vscode", "mcp.json");
    await installMcpConfig(path, baseConfig);
    const content = JSON.parse(await readFile(path, "utf-8"));
    expect(content.servers["hy3-data-mcp"].type).toBe("stdio");
  });

  it("writes a Continue config with an mcpServers array", async () => {
    const path = join(tempDir, ".continue", "config.json");
    await installMcpConfig(path, baseConfig);
    const content = JSON.parse(await readFile(path, "utf-8"));
    expect(Array.isArray(content.mcpServers)).toBe(true);
    expect(content.mcpServers[0].name).toBe("hy3-data-mcp");
  });

  it("updates an existing Continue object config into an array", async () => {
    const path = join(tempDir, ".continue", "config.json");
    await installMcpConfig(path, baseConfig);
    // second install should dedupe by name
    await installMcpConfig(path, { ...baseConfig, outputDir: "./updated" });
    const content = JSON.parse(await readFile(path, "utf-8"));
    expect(content.mcpServers).toHaveLength(1);
    expect(content.mcpServers[0].env.HY3_OUTPUT_DIR).toBe("./updated");
  });
});
