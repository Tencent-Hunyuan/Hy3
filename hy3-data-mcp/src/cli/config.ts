import { readFile, writeFile, mkdir } from "fs/promises";
import { basename, dirname } from "path";

export interface ServerConfig {
  apiKey: string;
  baseURL: string;
  model: string;
  outputDir: string;
}

function envFromConfig(config: ServerConfig): Record<string, string> {
  return {
    HY3_API_KEY: config.apiKey,
    HY3_BASE_URL: config.baseURL,
    HY3_MODEL: config.model,
    HY3_OUTPUT_DIR: config.outputDir,
  };
}

export function buildStandardMcpEntry(config: ServerConfig): Record<string, unknown> {
  return {
    type: "stdio",
    command: "npx",
    args: ["-y", "hy3-data-mcp"],
    env: envFromConfig(config),
  };
}

export function buildOpenCodeMcpEntry(config: ServerConfig): Record<string, unknown> {
  return {
    type: "local",
    command: ["npx", "-y", "hy3-data-mcp"],
    enabled: true,
    environment: envFromConfig(config),
  };
}

export function buildContinueMcpEntry(config: ServerConfig): Record<string, unknown> {
  return {
    name: "hy3-data-mcp",
    type: "stdio",
    command: "npx",
    args: ["-y", "hy3-data-mcp"],
    env: envFromConfig(config),
  };
}

export function buildVsCodeMcpEntry(config: ServerConfig): Record<string, unknown> {
  return {
    type: "stdio",
    command: "npx",
    args: ["-y", "hy3-data-mcp"],
    env: envFromConfig(config),
  };
}

function tomlString(value: unknown): string {
  if (typeof value === "string") {
    // Use basic TOML string with double quotes; reuse JSON escaping.
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) {
    return "[" + value.map(tomlString).join(", ") + "]";
  }
  if (typeof value === "object" && value !== null) {
    const entries = Object.entries(value).map(([k, v]) => `${k} = ${tomlString(v)}`);
    return "{ " + entries.join(", ") + " }";
  }
  return String(value);
}

function removeCodexServerSection(text: string, serverName: string): string {
  const prefix = `mcp_servers.${serverName}`;
  const lines = text.split("\n");
  const result: string[] = [];
  let skipping = false;

  for (const line of lines) {
    const headerMatch = line.match(/^\[\[?([^\]]+)\]\]?/);
    if (headerMatch) {
      const header = headerMatch[1];
      if (header === prefix || header.startsWith(`${prefix}.`)) {
        skipping = true;
        continue;
      }
      // Any other section header ends the skipped block.
      skipping = false;
    }
    if (!skipping) {
      result.push(line);
    }
  }

  return result.join("\n");
}

async function installCodexConfig(configPath: string, config: ServerConfig): Promise<void> {
  let text = "";
  try {
    text = await readFile(configPath, "utf-8");
  } catch {
    // file does not exist
  }

  // Remove any existing hy3-data-mcp server section and its nested tables.
  text = removeCodexServerSection(text, "hy3-data-mcp");

  // Ensure there's a top-level [mcp_servers] section (keeps Codex grouping clear).
  if (!/^\[mcp_servers\]\s*$/m.test(text)) {
    if (text.length > 0 && !text.endsWith("\n")) {
      text += "\n";
    }
    text += "[mcp_servers]\n";
  }

  const env = {
    HY3_API_KEY: config.apiKey,
    HY3_BASE_URL: config.baseURL,
    HY3_MODEL: config.model,
    HY3_OUTPUT_DIR: config.outputDir,
  };

  text += `\n[mcp_servers.hy3-data-mcp]\n`;
  text += `command = "npx"\n`;
  text += `args = ["-y", "hy3-data-mcp"]\n`;
  text += `env = ${tomlString(env)}\n`;

  await mkdir(dirname(configPath), { recursive: true });
  await writeFile(configPath, text, "utf-8");
}

export async function readJsonFile(path: string): Promise<Record<string, unknown>> {
  try {
    const content = await readFile(path, "utf-8");
    return JSON.parse(content);
  } catch {
    return {};
  }
}

export async function writeJsonFile(path: string, data: Record<string, unknown>): Promise<void> {
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, JSON.stringify(data, null, 2) + "\n", "utf-8");
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

export async function installMcpConfig(
  configPath: string,
  serverConfig: ServerConfig
): Promise<void> {
  if (isOpenCodeConfigPath(configPath)) {
    const existing = await readJsonFile(configPath);
    const entry = buildOpenCodeMcpEntry(serverConfig);
    const mcp = (existing.mcp as Record<string, unknown>) || {};
    const updated = {
      ...existing,
      mcp: {
        ...mcp,
        "hy3-data-mcp": entry,
      },
    };
    await writeJsonFile(configPath, updated);
    return;
  }

  if (isCodexConfigPath(configPath)) {
    await installCodexConfig(configPath, serverConfig);
    return;
  }

  if (isVsCodeMcpPath(configPath)) {
    const existing = await readJsonFile(configPath);
    const entry = buildVsCodeMcpEntry(serverConfig);
    const servers = (existing.servers as Record<string, unknown>) || {};
    const updated = {
      ...existing,
      servers: {
        ...servers,
        "hy3-data-mcp": entry,
      },
    };
    await writeJsonFile(configPath, updated);
    return;
  }

  if (isContinueConfigPath(configPath)) {
    const existing = await readJsonFile(configPath);
    const entry = buildContinueMcpEntry(serverConfig);
    const current = existing.mcpServers;

    let updatedMcpServers: unknown;
    if (Array.isArray(current)) {
      const filtered = current.filter(
        (item) =>
          !(typeof item === "object" && item !== null && "name" in item &&
            String((item as { name: string }).name).toLowerCase().includes("hy3-data-mcp"))
      );
      updatedMcpServers = [...filtered, entry];
    } else if (current && typeof current === "object") {
      updatedMcpServers = {
        ...(current as Record<string, unknown>),
        "hy3-data-mcp": buildStandardMcpEntry(serverConfig),
      };
    } else {
      updatedMcpServers = [entry];
    }

    const updated = {
      ...existing,
      mcpServers: updatedMcpServers,
    };
    await writeJsonFile(configPath, updated);
    return;
  }

  const existing = await readJsonFile(configPath);
  const entry = buildStandardMcpEntry(serverConfig);
  const servers = (existing.mcpServers as Record<string, unknown>) || {};
  const updated = {
    ...existing,
    mcpServers: {
      ...servers,
      "hy3-data-mcp": entry,
    },
  };
  await writeJsonFile(configPath, updated);
}
