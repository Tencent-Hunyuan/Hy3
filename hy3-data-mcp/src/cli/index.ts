#!/usr/bin/env node
import { readFile } from "fs/promises";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import { initCommand, mcpCommand } from "./init.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

async function getVersion(): Promise<string> {
  try {
    const pkg = JSON.parse(await readFile(join(__dirname, "..", "..", "package.json"), "utf-8"));
    return pkg.version ?? "unknown";
  } catch {
    return "unknown";
  }
}

const command = process.argv[2];

async function main() {
  switch (command) {
    case "init":
      await initCommand();
      break;
    case "mcp":
      await mcpCommand();
      break;
    case "--version":
    case "-v":
      console.log(await getVersion());
      break;
    case "--help":
    case "-h":
    case undefined:
      console.log("Usage: hdm <command>");
      console.log("");
      console.log("Commands:");
      console.log(
        "  init       Full interactive installer (create .env + configure MCP hosts)"
      );
      console.log(
        "  mcp        Configure/reconfigure MCP hosts only, reusing the existing .env"
      );
      console.log("  --version  Show installed version");
      console.log("  --help     Show this help message");
      break;
    default:
      console.error(`Unknown command: ${command}`);
      console.error("Run 'hdm --help' for usage.");
      process.exit(1);
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
