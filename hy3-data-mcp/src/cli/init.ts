import { intro, outro, multiselect, text, confirm, isCancel, cancel } from "@clack/prompts";
import pc from "picocolors";
import { existsSync } from "fs";
import { readFile, writeFile, stat, mkdir } from "fs/promises";
import { resolve, join } from "path";
import { homedir } from "os";
import { detectClients, type DetectedClient } from "./detect.js";
import { installMcpConfig } from "./config.js";

const DEFAULT_OUTPUT_DIR = "./hy3-data-mcp";

async function ensureEnvDir(dir: string): Promise<string> {
  if (!existsSync(dir)) {
    await mkdir(dir, { recursive: true });
  }
  return dir;
}

async function ensureEnvFile(envDir: string, apiKey: string): Promise<string> {
  await ensureEnvDir(envDir);
  const envPath = resolve(envDir, ".env");
  const lines = [
    "HY3_API_KEY=" + apiKey,
    "HY3_BASE_URL=https://tokenhub.tencentmaas.com/v1",
    "HY3_MODEL=hy3-preview",
    "HY3_OUTPUT_DIR=" + DEFAULT_OUTPUT_DIR,
  ];

  if (existsSync(envPath)) {
    const content = await readFile(envPath, "utf-8");
    if (content.includes("HY3_API_KEY=")) {
      const updated = content
        .split("\n")
        .map((line) => (line.startsWith("HY3_API_KEY=") ? "HY3_API_KEY=" + apiKey : line))
        .join("\n");
      await writeFile(envPath, updated, "utf-8");
    } else {
      await writeFile(envPath, content + "\n" + lines.join("\n") + "\n", "utf-8");
    }
  } else {
    await writeFile(envPath, lines.join("\n") + "\n", "utf-8");
  }
  return envPath;
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
  if (existsSync(join(cwd, "package.json"))) {
    return cwd;
  }
  const candidate = join(cwd, "hy3-data-mcp");
  if (await looksLikeProjectDir(candidate)) {
    return candidate;
  }
  return cwd;
}

function pickDefaultEnvDir(): string {
  return join(homedir(), "hy3-data-mcp");
}

export async function initCommand(): Promise<void> {
  intro(pc.cyan("🚀 Hy3 Data MCP Installer"));

  const apiKey = await text({
    message: "Enter your Hy3 / TokenHub API key:",
    placeholder: "sk-...",
    validate(value) {
      if (!value) return "API key is required";
      return undefined;
    },
  });

  if (isCancel(apiKey)) {
    cancel("Installation cancelled.");
    process.exit(0);
  }

  const baseURL = await text({
    message: "Hy3 Base URL:",
    initialValue: "https://tokenhub.tencentmaas.com/v1",
  });

  if (isCancel(baseURL)) {
    cancel("Installation cancelled.");
    process.exit(0);
  }

  const model = await text({
    message: "Hy3 model name:",
    initialValue: "hy3-preview",
  });

  if (isCancel(model)) {
    cancel("Installation cancelled.");
    process.exit(0);
  }

  const envDirInput = await text({
    message: "Directory for the shared .env file:",
    initialValue: pickDefaultEnvDir(),
    validate(value) {
      if (!value) return ".env directory is required";
      return undefined;
    },
  });

  if (isCancel(envDirInput)) {
    cancel("Installation cancelled.");
    process.exit(0);
  }

  const envDir = resolve(envDirInput as string);

  const defaultProjectDir = await pickDefaultProjectDir();
  const projectDirInput = await text({
    message: "Project directory for project-scoped MCP configs and output preview:",
    initialValue: defaultProjectDir,
    validate(value) {
      if (!value) return "Project directory is required";
      return undefined;
    },
  });

  if (isCancel(projectDirInput)) {
    cancel("Installation cancelled.");
    process.exit(0);
  }

  const projectDir = resolve(projectDirInput as string);
  if (!(await looksLikeProjectDir(projectDir))) {
    cancel(`Directory does not exist: ${projectDir}`);
    process.exit(1);
  }

  const detected = await detectClients(projectDir);
  const installed = detected.filter((c) => c.installed);

  if (installed.length === 0) {
    cancel(
      "No supported MCP hosts detected. Install one of: CodeBuddy / WorkBuddy, Cursor, Cline, Roo Code, Continue, Codex CLI, Claude Code, or OpenCode, then run 'hdm init' again."
    );
    process.exit(0);
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

  const shouldInstall = await confirm({
    message: `Install hy3-data-mcp into ${pc.yellow(String(paths.length))} selected host(s)?`,
  });

  if (isCancel(shouldInstall) || !shouldInstall) {
    cancel("Installation cancelled.");
    process.exit(0);
  }

  try {
    for (const targetPath of paths) {
      await installMcpConfig(targetPath, {
        apiKey: apiKey as string,
        baseURL: baseURL as string,
        model: model as string,
        outputDir: DEFAULT_OUTPUT_DIR,
      });
    }
    const envPath = await ensureEnvFile(envDir, apiKey as string);

    outro(pc.green("✅ hy3-data-mcp installed successfully!"));
    console.log(pc.gray("Next steps:"));
    console.log(pc.gray("  1. Restart your MCP client(s)."));
    console.log(pc.gray("  2. Try: 'Analyze ./sample_data/sales.csv with hy3_data_insight'"));
    for (const targetPath of paths) {
      console.log(pc.gray(`  • Config: ${targetPath}`));
    }
    console.log(pc.gray(`  • Environment file: ${envPath}`));
    console.log(pc.gray(`  • Generated outputs will go to: ${DEFAULT_OUTPUT_DIR} (relative to the opened project)`));
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    outro(pc.red(`❌ Installation failed: ${message}`));
    process.exit(1);
  }
}
