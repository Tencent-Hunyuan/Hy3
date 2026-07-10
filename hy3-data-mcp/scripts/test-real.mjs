import { config } from "dotenv";
config();

import { spawn } from "child_process";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const serverPath = join(__dirname, "..", "dist", "index.js");

const apiKey = process.env.HY3_API_KEY;
if (!apiKey) {
  console.error("请先设置 HY3_API_KEY 环境变量，或在项目根目录创建 .env 文件（参考 .env.example）");
  process.exit(1);
}

function send(stdin, message) {
  stdin.write(JSON.stringify(message) + "\n");
}

async function main() {
  const child = spawn("node", [serverPath], {
    env: {
      ...process.env,
      HY3_API_KEY: apiKey,
      HY3_BASE_URL: process.env.HY3_BASE_URL || "https://tokenhub.tencentmaas.com/v1",
      HY3_MODEL: process.env.HY3_MODEL || "hy3-preview",
      HY3_OUTPUT_DIR: process.env.HY3_OUTPUT_DIR || join(process.cwd(), "hy3-data-output"),
    },
    stdio: ["pipe", "pipe", "pipe"],
  });

  const responses = [];
  const stderr = [];

  child.stdout.on("data", (chunk) => {
    const text = chunk.toString("utf-8");
    for (const line of text.split("\n").filter((l) => l.trim())) {
      try {
        responses.push(JSON.parse(line));
      } catch {
        responses.push({ raw: line });
      }
    }
  });

  child.stderr.on("data", (chunk) => stderr.push(chunk.toString("utf-8")));

  // MCP handshake
  send(child.stdin, {
    jsonrpc: "2.0",
    id: 1,
    method: "initialize",
    params: {
      protocolVersion: "2024-11-05",
      capabilities: {},
      clientInfo: { name: "test-client", version: "0.1.0" },
    },
  });

  await new Promise((r) => setTimeout(r, 800));

  send(child.stdin, {
    jsonrpc: "2.0",
    method: "notifications/initialized",
  });

  await new Promise((r) => setTimeout(r, 200));

  // List tools
  send(child.stdin, {
    jsonrpc: "2.0",
    id: 2,
    method: "tools/list",
    params: {},
  });

  await new Promise((r) => setTimeout(r, 500));

  // Call a real tool
  const testTool = process.env.TEST_TOOL || "hy3_analyze";
  const toolArgs = process.env.TEST_ARGS
    ? JSON.parse(process.env.TEST_ARGS)
    : {
        data_file_path: join(__dirname, "..", "sample_data", "sales.csv"),
        question: "分析这份销售数据，找出前3个关键趋势和异常点",
        language: "zh",
      };

  console.log(`\n>> 调用工具: ${testTool}`);
  console.log(">> 参数:", JSON.stringify(toolArgs, null, 2));

  send(child.stdin, {
    jsonrpc: "2.0",
    id: 3,
    method: "tools/call",
    params: { name: testTool, arguments: toolArgs },
  });

  // Wait for Hy3 response (could take 10-30s)
  await new Promise((r) => setTimeout(r, 35000));

  child.kill();

  await new Promise((r) => child.on("close", r));

  console.log("\n==== 工具返回结果 ====");
  const toolResponse = responses.find((r) => r.id === 3);
  if (toolResponse?.result?.content) {
    for (const item of toolResponse.result.content) {
      console.log(item.text);
    }
  } else {
    console.log(JSON.stringify(toolResponse, null, 2));
  }

  if (stderr.length > 0) {
    console.log("\n==== 服务器 stderr ====");
    console.log(stderr.join(""));
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
