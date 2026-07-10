import { access, readFile } from "fs/promises";
import { homedir } from "os";
import { exec } from "child_process";
import { promisify } from "util";
import { basename, dirname, join, resolve } from "path";

const execAsync = promisify(exec);

export interface DetectedClient {
  id: string;
  name: string;
  configPath: string;
  scope: "project" | "global";
  format: "json" | "toml";
  installed: boolean;
  configured: boolean;
}

function home(...parts: string[]): string {
  return join(homedir(), ...parts);
}

interface Candidate {
  id: string;
  name: string;
  command?: string;
  getPaths: (root: string) => string[];
  getDefaultPath: (root: string) => string;
  scope: "project" | "global";
  format: "json" | "toml";
}

const CLIENT_CANDIDATES: Candidate[] = [
  {
    id: "codebuddy",
    name: "CodeBuddy / WorkBuddy",
    getPaths: () => [home(".codebuddy", "mcp.json")],
    getDefaultPath: () => home(".codebuddy", "mcp.json"),
    scope: "global",
    format: "json",
  },
  {
    id: "cursor",
    name: "Cursor",
    command: "cursor",
    getPaths: () => [home(".cursor", "mcp.json")],
    getDefaultPath: () => home(".cursor", "mcp.json"),
    scope: "global",
    format: "json",
  },
  {
    id: "cline",
    name: "Cline",
    command: "cline",
    getPaths: () => [clineMcpSettingsPath()],
    getDefaultPath: () => clineMcpSettingsPath(),
    scope: "global",
    format: "json",
  },
  {
    id: "roo",
    name: "Roo Code",
    command: "roo",
    getPaths: () => [rooMcpSettingsPath()],
    getDefaultPath: () => rooMcpSettingsPath(),
    scope: "global",
    format: "json",
  },
  {
    id: "continue",
    name: "Continue",
    command: "continue",
    getPaths: () => [home(".continue", "config.json")],
    getDefaultPath: () => home(".continue", "config.json"),
    scope: "global",
    format: "json",
  },
  {
    id: "codex",
    name: "OpenAI Codex CLI",
    command: "codex",
    getPaths: () => [home(".codex", "config.toml")],
    getDefaultPath: () => home(".codex", "config.toml"),
    scope: "global",
    format: "toml",
  },
  {
    id: "claude",
    name: "Claude Code",
    command: "claude",
    getPaths: () => [home(".claude.json")],
    getDefaultPath: () => home(".claude.json"),
    scope: "global",
    format: "json",
  },
  {
    id: "opencode",
    name: "OpenCode",
    command: "opencode",
    getPaths: (root) => [openCodeConfigPath(), join(root, "opencode.json")],
    getDefaultPath: () => openCodeConfigPath(),
    scope: "global",
    format: "json",
  },
];

function openCodeConfigPath(): string {
  return home(".config", "opencode", "opencode.json");
}

function clineMcpSettingsPath(): string {
  const extensionId = "saoudrizwan.claude-dev";
  const fileName = "cline_mcp_settings.json";
  if (process.platform === "win32") {
    return home("AppData", "Roaming", "Code", "User", "globalStorage", extensionId, "settings", fileName);
  }
  if (process.platform === "darwin") {
    return home(
      "Library",
      "Application Support",
      "Code",
      "User",
      "globalStorage",
      extensionId,
      "settings",
      fileName
    );
  }
  return home(".config", "Code", "User", "globalStorage", extensionId, "settings", fileName);
}

function rooMcpSettingsPath(): string {
  const extensionId = "rooveterinaryinc.roo-cline";
  const fileName = "mcp_settings.json";
  if (process.platform === "win32") {
    return home("AppData", "Roaming", "Code", "User", "globalStorage", extensionId, "settings", fileName);
  }
  if (process.platform === "darwin") {
    return home(
      "Library",
      "Application Support",
      "Code",
      "User",
      "globalStorage",
      extensionId,
      "settings",
      fileName
    );
  }
  return home(".config", "Code", "User", "globalStorage", extensionId, "settings", fileName);
}

async function exists(path: string): Promise<boolean> {
  try {
    await access(path);
    return true;
  } catch {
    return false;
  }
}

async function commandExists(command?: string): Promise<boolean> {
  if (!command) return false;
  try {
    const cmd = process.platform === "win32" ? `where ${command}` : `command -v ${command}`;
    await execAsync(cmd, { timeout: 3000 });
    return true;
  } catch {
    return false;
  }
}

function isOpenCodeConfigPath(path: string): boolean {
  return basename(path) === "opencode.json";
}

function isCodexConfigPath(path: string): boolean {
  return basename(path) === "config.toml" && dirname(path).endsWith(".codex");
}

function isVsCodeMcpPath(path: string): boolean {
  return basename(path) === "mcp.json" && dirname(path).endsWith(".vscode");
}

function isContinueConfigPath(path: string): boolean {
  return basename(path) === "config.json" && dirname(path).endsWith(".continue");
}

function hasHy3Server(entries: Record<string, unknown> | unknown[]): boolean {
  if (Array.isArray(entries)) {
    return entries.some(
      (entry) =>
        typeof entry === "object" &&
        entry !== null &&
        "name" in entry &&
        String((entry as { name: string }).name).toLowerCase().includes("hy3-data-mcp")
    );
  }
  return Object.keys(entries).some((key) => key.toLowerCase().includes("hy3-data-mcp"));
}

async function isConfigured(path: string): Promise<boolean> {
  if (!(await exists(path))) return false;

  try {
    if (isOpenCodeConfigPath(path)) {
      const content = await readFile(path, "utf-8");
      const config = JSON.parse(content);
      const mcp = config.mcp ?? {};
      return Object.keys(mcp).some((key) => key.toLowerCase().includes("hy3-data-mcp"));
    }

    if (isCodexConfigPath(path)) {
      const content = await readFile(path, "utf-8");
      return content.includes('[mcp_servers.hy3-data-mcp]');
    }

    const content = await readFile(path, "utf-8");
    const config = JSON.parse(content);

    if (isVsCodeMcpPath(path)) {
      return hasHy3Server((config.servers as Record<string, unknown>) ?? {});
    }

    if (isContinueConfigPath(path)) {
      const servers = config.mcpServers;
      if (Array.isArray(servers)) return hasHy3Server(servers);
      return hasHy3Server((servers as Record<string, unknown>) ?? {});
    }

    const servers = config.mcpServers ?? config.servers ?? config.mcp?.servers ?? {};
    return hasHy3Server(servers);
  } catch {
    return false;
  }
}

export async function detectClients(baseDir?: string): Promise<DetectedClient[]> {
  const found: DetectedClient[] = [];
  const root = baseDir ? resolve(baseDir) : process.cwd();

  for (const candidate of CLIENT_CANDIDATES) {
    const paths = candidate.getPaths(root);
    const defaultPath = candidate.getDefaultPath(root);

    const pathStatuses = await Promise.all(
      paths.map(async (p) => ({ path: p, exists: await exists(p) }))
    );
    const existingPath = pathStatuses.find((s) => s.exists)?.path;
    const targetPath = existingPath ?? defaultPath;

    const hasCommand = await commandExists(candidate.command);
    const hasConfigFile = pathStatuses.some((s) => s.exists);
    const hasConfigDir = await exists(join(targetPath, ".."));
    const installed = hasCommand || hasConfigFile || hasConfigDir;

    found.push({
      id: candidate.id,
      name: candidate.name,
      configPath: targetPath,
      scope: candidate.scope,
      format: candidate.format,
      installed,
      configured: await isConfigured(targetPath),
    });
  }

  return found;
}

export function getDefaultConfigPath(clientId: string): string {
  const root = process.cwd();
  switch (clientId) {
    case "codebuddy":
      return home(".codebuddy", "mcp.json");
    case "cursor":
      return home(".cursor", "mcp.json");
    case "cline":
      return home(
        "AppData",
        "Roaming",
        "Code",
        "User",
        "globalStorage",
        "saoudrizwan.claude-dev",
        "settings",
        "cline_mcp_settings.json"
      );
    case "roo":
      return rooMcpSettingsPath();
    case "continue":
      return join(root, ".continue", "config.json");
    case "codex":
      return home(".codex", "config.toml");
    case "claude":
      return home(".claude.json");
    case "opencode":
      return openCodeConfigPath();
    default:
      return join(root, ".mcp.json");
  }
}
