import { intro, outro, multiselect, text, confirm, isCancel, cancel, note } from "@clack/prompts";
import pc from "picocolors";
import { existsSync } from "fs";
import { readFile, writeFile, stat, mkdir } from "fs/promises";
import { resolve, join, dirname } from "path";
import { homedir } from "os";
import { config as dotenvParse } from "dotenv";
import { detectClients, type DetectedClient } from "./detect.js";
import { installMcpConfig, type ServerConfig } from "./config.js";

const DEFAULT_OUTPUT_DIR = "./hy3-data-output";
const DEFAULT_ENV_DIR = join(homedir(), ".hy3-data-mcp");
const DEFAULT_BASE_URL = "https://tokenhub.tencentmaas.com/v1";
const DEFAULT_MODEL = "hy3-preview";

async function ensureEnvDir(dir: string): Promise<void> {
  if (!existsSync(dir)) {
    await mkdir(dir, { recursive: true });
  }
}

async function writeEnvFile(envDir: string, config: ServerConfig): Promise<string> {
  await ensureEnvDir(envDir);
  const envPath = resolve(envDir, ".env");
  const lines = [
    "HY3_API_KEY=" + config.apiKey,
    "HY3_BASE_URL=" + config.baseURL,
    "HY3_MODEL=" + config.model,
    "HY3_OUTPUT_DIR=" + config.outputDir,
  ];

  if (existsSync(envPath)) {
    const content = await readFile(envPath, "utf-8");
    const merged = new Map<string, string>();
    for (const line of content.split("\n")) {
      const idx = line.indexOf("=");
      if (idx > 0) {
        merged.set(line.slice(0, idx), line.slice(idx + 1));
      }
    }
    merged.set("HY3_API_KEY", config.apiKey);
    merged.set("HY3_BASE_URL", config.baseURL);
    merged.set("HY3_MODEL", config.model);
    merged.set("HY3_OUTPUT_DIR", config.outputDir);
    await writeFile(
      envPath,
      Array.from(merged.entries())
        .map(([k, v]) => `${k}=${v}`)
        .join("\n") + "\n",
      "utf-8"
    );
  } else {
    await writeFile(envPath, lines.join("\n") + "\n", "utf-8");
  }
  return envPath;
}

async function readEnvConfig(envDir: string): Promise<(ServerConfig & { envPath: string }) | null> {
  const envPath = resolve(envDir, ".env");
  if (!existsSync(envPath)) {
    return null;
  }
  const result = dotenvParse({ path: envPath });
  const parsed = result.parsed;
  if (!parsed?.HY3_API_KEY) {
    return null;
  }
  return {
    apiKey: parsed.HY3_API_KEY,
    baseURL: parsed.HY3_BASE_URL || DEFAULT_BASE_URL,
    model: parsed.HY3_MODEL || DEFAULT_MODEL,
    outputDir: parsed.HY3_OUTPUT_DIR || DEFAULT_OUTPUT_DIR,
    envPath,
  };
}

function clientLabel(client: DetectedClient): string {
  const status = client.configured ? "already configured" : "not configured";
  return `${client.name} (${status} | scope: ${client.scope})`;
}

async function looksLikeProjectDir(dir: string): Promise<boolean> {
  try {
    const s = await stat(dir);
    return s.isDirectory();
  } catch {
    return false;
  }
}

async function pickDefaultProjectDir(): Promise<string> {
  const cwd = process.cwd();
  let dir = cwd;
  while (true) {
    if (existsSync(join(dir, ".git")) || existsSync(join(dir, "package.json"))) {
      return dir;
    }
    const parent = dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  const candidate = join(cwd, "hy3-data-mcp");
  if (await looksLikeProjectDir(candidate)) {
    return candidate;
  }
  return cwd;
}

async function askApiKey(): Promise<string> {
  const value = await text({
    message: "Enter your Hy3 / TokenHub API key:",
    placeholder: "sk-...",
    validate(value) {
      if (!value) return "API key is required";
      return undefined;
    },
  });
  if (isCancel(value)) {
    cancel("Installation cancelled.");
    process.exit(0);
  }
  return value as string;
}

async function askBaseURL(): Promise<string> {
  const value = await text({
    message: "Hy3 Base URL:",
    initialValue: DEFAULT_BASE_URL,
  });
  if (isCancel(value)) {
    cancel("Installation cancelled.");
    process.exit(0);
  }
  return (value as string) || DEFAULT_BASE_URL;
}

async function askModel(): Promise<string> {
  const value = await text({
    message: "Hy3 model name:",
    initialValue: DEFAULT_MODEL,
  });
  if (isCancel(value)) {
    cancel("Installation cancelled.");
    process.exit(0);
  }
  return (value as string) || DEFAULT_MODEL;
}

async function askEnvDir(): Promise<string> {
  const value = await text({
    message: "Directory for the shared .env file:",
    initialValue: DEFAULT_ENV_DIR,
    validate(value) {
      if (!value) return ".env directory is required";
      return undefined;
    },
  });
  if (isCancel(value)) {
    cancel("Installation cancelled.");
    process.exit(0);
  }
  return resolve(value as string);
}

async function selectHosts(detected: DetectedClient[]): Promise<string[]> {
  const installed = detected.filter((c) => c.installed);
  const notInstalled = detected.filter((c) => !c.installed);

  if (installed.length === 0) {
    cancel(
      "No supported MCP hosts detected. Install one of: CodeBuddy / WorkBuddy, Cursor, Cline, Roo Code, Continue, Codex CLI, Claude Code, or OpenCode, then run 'hdm init' again."
    );
    process.exit(0);
  }

  if (notInstalled.length > 0) {
    const list = notInstalled.map((c) => `• ${c.name}`).join("\n");
    note(list, "Supported but not installed");
  }

  const options = installed.map((client) => ({
    value: client.configPath,
    label: clientLabel(client),
    hint: client.configPath,
  }));

  const selected = await multiselect<string>({
    message: "Select the MCP hosts to configure (space to toggle, enter to confirm):",
    options,
    required: true,
  });

  if (isCancel(selected)) {
    cancel("Installation cancelled.");
    process.exit(0);
  }

  const paths = selected as string[];
  if (paths.length === 0) {
    cancel("No MCP hosts selected.");
    process.exit(0);
  }
  return paths;
}

async function confirmInstall(paths: string[]): Promise<void> {
  const shouldInstall = await confirm({
    message: `Install hy3-data-mcp into ${pc.yellow(String(paths.length))} selected host(s)?`,
  });

  if (isCancel(shouldInstall) || !shouldInstall) {
    cancel("Installation cancelled.");
    process.exit(0);
  }
}

async function installIntoHosts(paths: string[], config: ServerConfig, projectDir: string): Promise<void> {
  for (const targetPath of paths) {
    await installMcpConfig(targetPath, config, projectDir);
  }
}

async function finalize(paths: string[], envPath: string): Promise<void> {
  outro(pc.green("✅ hy3-data-mcp installed successfully!"));
  console.log(pc.gray("Next steps:"));
  console.log(pc.gray("  1. Restart your MCP client(s)."));
  console.log(pc.gray("  2. Try: 'Analyze ./sample_data/sales.csv with hy3_data_insight'"));
  for (const targetPath of paths) {
    console.log(pc.gray(`  • Config: ${targetPath}`));
  }
  console.log(pc.gray(`  • Environment file: ${envPath}`));
  console.log(pc.gray(`  • Generated outputs will go to: ${DEFAULT_OUTPUT_DIR} (relative to the opened project)`));
}

export async function initCommand(): Promise<void> {
  intro(pc.cyan("🚀 Hy3 Data MCP Installer"));

  const apiKey = await askApiKey();
  const baseURL = await askBaseURL();
  const model = await askModel();
  const envDir = await askEnvDir();
  const projectDir = await pickDefaultProjectDir();

  const detected = await detectClients(projectDir);
  const paths = await selectHosts(detected);
  await confirmInstall(paths);

  try {
    const config: ServerConfig = { apiKey, baseURL, model, outputDir: DEFAULT_OUTPUT_DIR };
    await installIntoHosts(paths, config, projectDir);
    const envPath = await writeEnvFile(envDir, config);
    await finalize(paths, envPath);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    outro(pc.red(`❌ Installation failed: ${message}`));
    process.exit(1);
  }
}

export async function mcpCommand(): Promise<void> {
  intro(pc.cyan("🔌 Hy3 Data MCP Host Configurator"));

  const envDir = await askEnvDir();
  let envConfig = await readEnvConfig(envDir);

  if (!envConfig) {
    console.log(pc.yellow("No valid .env found. Let's create one first."));
    const apiKey = await askApiKey();
    const baseURL = await askBaseURL();
    const model = await askModel();
    const config: ServerConfig = { apiKey, baseURL, model, outputDir: DEFAULT_OUTPUT_DIR };
    const envPath = await writeEnvFile(envDir, config);
    envConfig = { ...config, envPath };
  }

  const projectDir = await pickDefaultProjectDir();
  const detected = await detectClients(projectDir);
  const paths = await selectHosts(detected);
  await confirmInstall(paths);

  try {
    await installIntoHosts(paths, envConfig, projectDir);
    await finalize(paths, envConfig.envPath);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    outro(pc.red(`❌ Configuration failed: ${message}`));
    process.exit(1);
  }
}
