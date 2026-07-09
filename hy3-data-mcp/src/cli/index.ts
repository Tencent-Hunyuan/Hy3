#!/usr/bin/env node
import { initCommand } from "./init.js";

const command = process.argv[2];

async function main() {
  switch (command) {
    case "init":
      await initCommand();
      break;
    case "--help":
    case "-h":
    case undefined:
      console.log("Usage: hdm <command>");
      console.log("");
      console.log("Commands:");
      console.log("  init   Interactive installer to configure hy3-data-mcp for your MCP client");
      console.log("  --help Show this help message");
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
