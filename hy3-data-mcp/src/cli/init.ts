import { intro, outro, select, text, confirm, isCancel, cancel } from "@clack/prompts";
import pc from "picocolors";
import { existsSync } from "fs";
import { readFile, writeFile } from "fs/promises";
import { resolve } from "path";
import { detectClients } from "./detect.js";
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

export async function initCommand(): Promise<void> {
  intro(pc.cyan("🚀 Hy3 Data MCP Installer"));

  const detected = await detectClients();

  const choices = detected.map((client) => ({
    value: client.configPath,
    label: `${client.name} (${client.scope})`,
    hint: client.configPath,
  }));

  choices.push({
    value: "__manual__",
    label: "Manually specify a config path",
    hint: "",
  });

  const configPath = await select({
    message: "Select the MCP client to configure:",
    options: choices,
  });

  if (isCancel(configPath)) {
    cancel("Installation cancelled.");
    process.exit(0);
  }

  let targetPath: string = configPath as string;
  if (targetPath === "__manual__") {
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
    targetPath = manualPath as string;
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
    message: `Install hy3-data-mcp into ${pc.yellow(targetPath)}?`,
  });

  if (isCancel(shouldInstall) || !shouldInstall) {
    cancel("Installation cancelled.");
    process.exit(0);
  }

  try {
    await installMcpConfig(targetPath, {
      apiKey: apiKey as string,
      baseURL: baseURL as string,
      model: model as string,
      outputDir: outputDir as string,
    });
    await ensureEnvFile(apiKey as string);

    outro(pc.green("✅ hy3-data-mcp installed successfully!"));
    console.log(pc.gray("Next steps:"));
    console.log(pc.gray("  1. Restart your MCP client."));
    console.log(pc.gray("  2. Try: 'Analyze ./sample_data/sales.csv with hy3_data_insight'"));
    console.log(pc.gray(`  3. Generated config: ${targetPath}`));
    console.log(pc.gray(`  4. Environment file: ${resolve(process.cwd(), ".env")}`));
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    outro(pc.red(`❌ Installation failed: ${message}`));
    process.exit(1);
  }
}
