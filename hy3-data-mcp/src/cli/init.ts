import { intro, outro, multiselect, text, confirm, isCancel, cancel } from "@clack/prompts";
import pc from "picocolors";
import { existsSync } from "fs";
import { readFile, writeFile } from "fs/promises";
import { resolve } from "path";
import { detectClients, type DetectedClient } from "./detect.js";
import { installMcpConfig } from "./config.js";

async function ensureEnvFile(apiKey: string): Promise<void> {
  const envPath = resolve(process.cwd(), ".env");
  const lines = [
    "HY3_API_KEY=" + apiKey,
    "HY3_BASE_URL=https://tokenhub.tencentmaas.com/v1",
    "HY3_MODEL=hy3-preview",
    "HY3_OUTPUT_DIR=./hy3-mcp-output",
  ];

  if (existsSync(envPath)) {
    const content = await readFile(envPath, "utf-8");
    if (content.includes("HY3_API_KEY=")) {
      const updated = content
        .split("\n")
        .map((line) => (line.startsWith("HY3_API_KEY=") ? "HY3_API_KEY=" + apiKey : line))
        .join("\n");
      await writeFile(envPath, updated, "utf-8");
      return;
    }
    await writeFile(envPath, content + "\n" + lines.join("\n") + "\n", "utf-8");
  } else {
    await writeFile(envPath, lines.join("\n") + "\n", "utf-8");
  }
}

function clientLabel(client: DetectedClient): string {
  const status = client.installed
    ? client.configured
      ? "already configured"
      : "not configured"
    : "not installed";
  return `${client.name} (${status} | scope: ${client.scope})`;
}

export async function initCommand(): Promise<void> {
  intro(pc.cyan("🚀 Hy3 Data MCP Installer"));

  const detected = await detectClients();
  const installed = detected.filter((c) => c.installed);

  const options = installed.map((client) => ({
    value: client.configPath,
    label: clientLabel(client),
    hint: client.configPath,
  }));

  options.push({
    value: "__manual__",
    label: "Manually specify a config path",
    hint: "",
  });

  const selected = await multiselect<string>({
    message: "Select the MCP hosts to configure (space to toggle, enter to confirm):",
    options,
    required: false,
  });

  if (isCancel(selected)) {
    cancel("Installation cancelled.");
    process.exit(0);
  }

  const paths = (selected as string[]).filter((p) => p !== "__manual__");
  const manualRequested = (selected as string[]).includes("__manual__");

  if (manualRequested) {
    const manualPath = await text({
      message: "Enter the full path to the MCP config file:",
      placeholder: "/path/to/mcp-config.json",
      validate(value) {
        if (!value) return "Path is required";
        return undefined;
      },
    });
    if (isCancel(manualPath)) {
      cancel("Installation cancelled.");
      process.exit(0);
    }
    paths.push(manualPath as string);
  }

  if (paths.length === 0) {
    cancel("No MCP hosts selected.");
    process.exit(0);
  }

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

  const outputDir = await text({
    message: "Output directory for generated charts:",
    initialValue: "./hy3-mcp-output",
  });

  if (isCancel(outputDir)) {
    cancel("Installation cancelled.");
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
        outputDir: outputDir as string,
      });
    }
    await ensureEnvFile(apiKey as string);

    outro(pc.green("✅ hy3-data-mcp installed successfully!"));
    console.log(pc.gray("Next steps:"));
    console.log(pc.gray("  1. Restart your MCP client(s)."));
    console.log(pc.gray("  2. Try: 'Analyze ./sample_data/sales.csv with hy3_data_insight'"));
    for (const targetPath of paths) {
      console.log(pc.gray(`  • Config: ${targetPath}`));
    }
    console.log(pc.gray(`  • Environment file: ${resolve(process.cwd(), ".env")}`));
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    outro(pc.red(`❌ Installation failed: ${message}`));
    process.exit(1);
  }
}
