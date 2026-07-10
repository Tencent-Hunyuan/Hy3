import { readFile, writeFile, mkdir } from "fs/promises";
import { basename, dirname } from "path";

export interface ServerConfig {
  apiKey: string;
  baseURL: string;
  model: string;
  outputDir: string;
}

export function buildMcpServerEntry(config: ServerConfig): Record<string, unknown> {
  return {
    command: "npx",
    args: ["-y", "hy3-data-mcp"],
    env: {
      HY3_API_KEY: config.apiKey,
      HY3_BASE_URL: config.baseURL,
      HY3_MODEL: config.model,
      HY3_OUTPUT_DIR: config.outputDir,
    },
  };
}

export function buildOpenCodeMcpEntry(config: ServerConfig): Record<string, unknown> {
  return {
    type: "local",
    command: ["npx", "-y", "hy3-data-mcp"],
    enabled: true,
    environment: {
      HY3_API_KEY: config.apiKey,
      HY3_BASE_URL: config.baseURL,
      HY3_MODEL: config.model,
      HY3_OUTPUT_DIR: config.outputDir,
    },
  };
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

export async function installMcpConfig(
  configPath: string,
  serverConfig: ServerConfig
): Promise<void> {
  const existing = await readJsonFile(configPath);

  if (basename(configPath) === "opencode.json") {
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

  const entry = buildMcpServerEntry(serverConfig);
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
