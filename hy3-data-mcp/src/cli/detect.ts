import { access } from "fs/promises";
import { homedir } from "os";
import { join, resolve } from "path";

export interface DetectedClient {
  id: string;
  name: string;
  configPath: string;
  scope: "project" | "global";
  format: "json";
}

function home(...parts: string[]): string {
  return join(homedir(), ...parts);
}

interface Candidate {
  id: string;
  name: string;
  getPaths: (root: string) => string[];
  scope: "project" | "global";
}

const CLIENT_CANDIDATES: Candidate[] = [
  {
    id: "codebuddy",
    name: "CodeBuddy / WorkBuddy",
    getPaths: (root) => [join(root, ".codebuddy", "mcp.json")],
    scope: "project",
  },
  {
    id: "cursor",
    name: "Cursor",
    getPaths: (root) => [join(root, ".cursor", "mcp.json"), home(".cursor", "mcp.json")],
    scope: "project",
  },
  {
    id: "cline",
    name: "Cline",
    getPaths: (root) => [
      join(root, ".vscode", "mcp.json"),
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
    scope: "global",
  },
  {
    id: "roo",
    name: "Roo Code",
    getPaths: (root) => [join(root, ".roo", "mcp.json"), home(".roo", "mcp.json")],
    scope: "global",
  },
  {
    id: "continue",
    name: "Continue",
    getPaths: (root) => [join(root, ".continue", "config.json"), home(".continue", "config.json")],
    scope: "global",
  },
  {
    id: "codex",
    name: "OpenAI Codex CLI",
    getPaths: () => [home(".codex", "config.json"), home(".codex", "mcp.json")],
    scope: "global",
  },
  {
    id: "opencodes",
    name: "OpenCode / OpenCodes",
    getPaths: () => [home(".opencodes", "mcp.json"), home(".opencode", "mcp.json")],
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

export async function detectClients(baseDir?: string): Promise<DetectedClient[]> {
  const found: DetectedClient[] = [];
  const seen = new Set<string>();
  const root = baseDir ? resolve(baseDir) : process.cwd();

  for (const candidate of CLIENT_CANDIDATES) {
    for (const path of candidate.getPaths(root)) {
      if (seen.has(path)) continue;
      if (await exists(path)) {
        seen.add(path);
        found.push({
          id: candidate.id,
          name: candidate.name,
          configPath: path,
          scope: candidate.scope,
          format: "json",
        });
      }
    }
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
    case "opencodes":
      return home(".opencodes", "mcp.json");
    default:
      return join(root, "mcp-config.json");
  }
}
