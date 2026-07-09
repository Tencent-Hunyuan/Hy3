import { access, readFile } from "fs/promises";
import { homedir } from "os";
import { exec } from "child_process";
import { promisify } from "util";
import { join, resolve } from "path";

const execAsync = promisify(exec);

export interface DetectedClient {
  id: string;
  name: string;
  configPath: string;
  scope: "project" | "global";
  format: "json";
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
}

const CLIENT_CANDIDATES: Candidate[] = [
  {
    id: "codebuddy",
    name: "CodeBuddy / WorkBuddy",
    getPaths: (root) => [join(root, ".codebuddy", "mcp.json")],
    getDefaultPath: (root) => join(root, ".codebuddy", "mcp.json"),
    scope: "project",
  },
  {
    id: "cursor",
    name: "Cursor",
    getPaths: (root) => [join(root, ".cursor", "mcp.json"), home(".cursor", "mcp.json")],
    getDefaultPath: (root) => join(root, ".cursor", "mcp.json"),
    scope: "project",
  },
  {
    id: "cline",
    name: "Cline",
    getPaths: (root) => [
      join(root, ".vscode", "mcp.json"),
      home(
        "AppData",
        "Roaming",
        "Code",
        "User",
        "globalStorage",
        "saoudrizwan.claude-dev",
        "settings",
        "cline_mcp_settings.json"
      ),
      home(
        ".config",
        "Code",
        "User",
        "globalStorage",
        "saoudrizwan.claude-dev",
        "settings",
        "cline_mcp_settings.json"
      ),
    ],
    getDefaultPath: (root) => join(root, ".vscode", "mcp.json"),
    scope: "global",
  },
  {
    id: "roo",
    name: "Roo Code",
    getPaths: (root) => [join(root, ".roo", "mcp.json"), home(".roo", "mcp.json")],
    getDefaultPath: (root) => join(root, ".roo", "mcp.json"),
    scope: "global",
  },
  {
    id: "continue",
    name: "Continue",
    getPaths: (root) => [join(root, ".continue", "config.json"), home(".continue", "config.json")],
    getDefaultPath: (root) => join(root, ".continue", "config.json"),
    scope: "global",
  },
  {
    id: "codex",
    name: "OpenAI Codex CLI",
    command: "codex",
    getPaths: () => [home(".codex", "config.json"), home(".codex", "mcp.json")],
    getDefaultPath: () => home(".codex", "config.json"),
    scope: "global",
  },
  {
    id: "claude",
    name: "Claude Code",
    command: "claude",
    getPaths: () => [home(".claude", "config.json"), home(".claude", "mcp.json")],
    getDefaultPath: () => home(".claude", "config.json"),
    scope: "global",
  },
  {
    id: "opencodes",
    name: "OpenCode / OpenCodes",
    command: "opencode",
    getPaths: () => [home(".opencodes", "mcp.json"), home(".opencode", "mcp.json")],
    getDefaultPath: () => home(".opencodes", "mcp.json"),
    scope: "global",
  },
];

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

async function isConfigured(path: string): Promise<boolean> {
  if (!(await exists(path))) return false;
  try {
    const content = await readFile(path, "utf-8");
    const config = JSON.parse(content);
    const servers = config.mcpServers ?? config.servers ?? config.mcp?.servers ?? {};
    return Object.keys(servers).some((key) => key.toLowerCase().includes("hy3-data-mcp"));
  } catch {
    return false;
  }
}

export async function detectClients(baseDir?: string): Promise<DetectedClient[]> {
  const found: DetectedClient[] = [];
  const seen = new Set<string>();
  const root = baseDir ? resolve(baseDir) : process.cwd();

  for (const candidate of CLIENT_CANDIDATES) {
    const paths = candidate.getPaths(root);
    const defaultPath = candidate.getDefaultPath(root);

    const pathStatuses = await Promise.all(
      paths.map(async (p) => ({ path: p, exists: await exists(p) }))
    );
    const existingPath = pathStatuses.find((s) => s.exists)?.path;
    const targetPath = existingPath ?? defaultPath;

    if (seen.has(targetPath)) continue;
    seen.add(targetPath);

    const hasCommand = await commandExists(candidate.command);
    const hasConfigFile = pathStatuses.some((s) => s.exists);
    const hasConfigDir = await exists(join(targetPath, ".."));
    const installed = hasCommand || hasConfigFile || hasConfigDir;

    found.push({
      id: candidate.id,
      name: candidate.name,
      configPath: targetPath,
      scope: candidate.scope,
      format: "json",
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
      return join(root, ".codebuddy", "mcp.json");
    case "cursor":
      return join(root, ".cursor", "mcp.json");
    case "cline":
      return join(root, ".vscode", "mcp.json");
    case "roo":
      return join(root, ".roo", "mcp.json");
    case "continue":
      return join(root, ".continue", "config.json");
    case "codex":
      return home(".codex", "config.json");
    case "claude":
      return home(".claude", "config.json");
    case "opencodes":
      return home(".opencodes", "mcp.json");
    default:
      return join(root, "mcp-config.json");
  }
}
