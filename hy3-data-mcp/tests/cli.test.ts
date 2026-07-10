import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtemp, mkdir, writeFile, readFile, rm } from "fs/promises";
import { tmpdir } from "os";
import { dirname, join } from "path";
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

  it("detects Continue config in ~/.continue/config.json", async () => {
    const originalUserProfile = process.env.USERPROFILE;
    const originalHome = process.env.HOME;
    process.env.USERPROFILE = tempDir;
    process.env.HOME = tempDir;

    const { detectClients } = await import("../src/cli/detect.js");
    await mkdir(join(tempDir, ".continue"), { recursive: true });
    await writeFile(join(tempDir, ".continue", "config.json"), "{}", "utf-8");

    const clients = await detectClients(tempDir);
    const cont = clients.find((c) => c.id === "continue");
    expect(cont).toBeDefined();
    expect(cont?.configPath).toBe(join(tempDir, ".continue", "config.json"));

    process.env.USERPROFILE = originalUserProfile;
    process.env.HOME = originalHome;
  });

  it("does not pick project .continue/config.json for Continue", async () => {
    const originalUserProfile = process.env.USERPROFILE;
    const originalHome = process.env.HOME;
    process.env.USERPROFILE = tempDir;
    process.env.HOME = tempDir;

    const { detectClients } = await import("../src/cli/detect.js");
    await mkdir(join(tempDir, ".continue"), { recursive: true });
    await writeFile(join(tempDir, ".continue", "config.json"), "{}", "utf-8");

    const clients = await detectClients(join(tempDir, "project"));
    const cont = clients.find((c) => c.id === "continue");
    expect(cont?.configPath).toBe(join(tempDir, ".continue", "config.json"));

    process.env.USERPROFILE = originalUserProfile;
    process.env.HOME = originalHome;
  });

  it("detects Claude Code config in ~/.claude.json", async () => {
    const originalUserProfile = process.env.USERPROFILE;
    const originalHome = process.env.HOME;
    process.env.USERPROFILE = tempDir;
    process.env.HOME = tempDir;

    const { detectClients } = await import("../src/cli/detect.js");
    await writeFile(join(tempDir, ".claude.json"), "{}", "utf-8");

    const clients = await detectClients(tempDir);
    const claude = clients.find((c) => c.id === "claude");
    expect(claude).toBeDefined();
    expect(claude?.configPath).toBe(join(tempDir, ".claude.json"));

    process.env.USERPROFILE = originalUserProfile;
    process.env.HOME = originalHome;
  });

  it("detects Cursor config in ~/.cursor/mcp.json", async () => {
    const originalUserProfile = process.env.USERPROFILE;
    const originalHome = process.env.HOME;
    process.env.USERPROFILE = tempDir;
    process.env.HOME = tempDir;

    const { detectClients } = await import("../src/cli/detect.js");
    await mkdir(join(tempDir, ".cursor"), { recursive: true });
    await writeFile(join(tempDir, ".cursor", "mcp.json"), "{}", "utf-8");

    const clients = await detectClients(join(tempDir, "project"));
    const cursor = clients.find((c) => c.id === "cursor");
    expect(cursor).toBeDefined();
    expect(cursor?.configPath).toBe(join(tempDir, ".cursor", "mcp.json"));

    process.env.USERPROFILE = originalUserProfile;
    process.env.HOME = originalHome;
  });

  it("detects Roo Code global config", async () => {
    const originalUserProfile = process.env.USERPROFILE;
    const originalHome = process.env.HOME;
    process.env.USERPROFILE = tempDir;
    process.env.HOME = tempDir;

    const { detectClients } = await import("../src/cli/detect.js");
    const rooPath = join(
      tempDir,
      "AppData",
      "Roaming",
      "Code",
      "User",
      "globalStorage",
      "rooveterinaryinc.roo-cline",
      "settings",
      "mcp_settings.json"
    );
    await mkdir(dirname(rooPath), { recursive: true });
    await writeFile(rooPath, "{}", "utf-8");

    const clients = await detectClients(join(tempDir, "project"));
    const roo = clients.find((c) => c.id === "roo");
    expect(roo).toBeDefined();
    expect(roo?.configPath).toBe(rooPath);

    process.env.USERPROFILE = originalUserProfile;
    process.env.HOME = originalHome;
  });

  it("writes Claude Code user config under projects key", async () => {
    const configPath = join(tempDir, ".claude.json");
    const projectDir = join(tempDir, "my-project");
    await installMcpConfig(
      configPath,
      {
        apiKey: "test-key",
        baseURL: "https://tokenhub.tencentmaas.com/v1",
        model: "hy3-preview",
        outputDir: "./hy3-data-output",
      },
      projectDir
    );

    const content = JSON.parse(await readFile(configPath, "utf-8"));
    expect(content.projects[projectDir].mcpServers["hy3-data-mcp"]).toBeDefined();
    expect(content.projects[projectDir].mcpServers["hy3-data-mcp"].env.HY3_API_KEY).toBe("test-key");
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
