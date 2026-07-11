#!/usr/bin/env node
import { config } from "dotenv";
config();

import { startServer } from "./server.js";

startServer().catch((error) => {
  console.error("Fatal error starting Hy3 MCP Server:", error);
  process.exit(1);
});
