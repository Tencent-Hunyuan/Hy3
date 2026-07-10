import { describe, it, expect } from "vitest";
import { spawn } from "child_process";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const serverPath = join(__dirname, "..", "dist", "index.js");

function sendRequest(child: ReturnType<typeof spawn>, message: object): void {
  child.stdin?.write(JSON.stringify(message) + "\n");
}

async function callServer(requests: object[], waitMs = 2000): Promise<unknown[]> {
  return new Promise((resolve, reject) => {
    const child = spawn("node", [serverPath], {
      env: {
        ...process.env,
        HY3_API_KEY: "fake-key-for-smoke-test",
        HY3_BASE_URL: "https://tokenhub.tencentmaas.com/v1",
        HY3_MODEL: "hy3-preview",
      },
      stdio: ["pipe", "pipe", "pipe"],
    });

    const stdoutBuffers: Buffer[] = [];
    const stderrBuffers: Buffer[] = [];

    child.stdout.on("data", (chunk) => stdoutBuffers.push(chunk));
    child.stderr.on("data", (chunk) => stderrBuffers.push(chunk));

    for (const request of requests) {
      sendRequest(child, request);
    }
    child.stdin?.end();

    setTimeout(() => {
      child.kill();
    }, waitMs);

    child.on("close", () => {
      const stderr = Buffer.concat(stderrBuffers).toString("utf-8");
      if (stderr) {
        // Log stderr for debugging but don't fail
        console.error("Server stderr:", stderr);
      }
      const lines = Buffer.concat(stdoutBuffers)
        .toString("utf-8")
        .split("\n")
        .filter((line) => line.trim());

      const responses = lines.map((line) => {
        try {
          return JSON.parse(line);
        } catch {
          return { raw: line };
        }
      });
      resolve(responses);
    });

    child.on("error", reject);
  });
}

describe("MCP server smoke test", () => {
  it(
    "responds to ListTools request",
    async () => {
      const responses = await callServer(
      [
        {
          jsonrpc: "2.0",
          id: 1,
          method: "initialize",
          params: {
            protocolVersion: "2024-11-05",
            capabilities: {},
            clientInfo: { name: "test-client", version: "0.1.0" },
          },
        },
        {
          jsonrpc: "2.0",
          method: "notifications/initialized",
        },
        {
          jsonrpc: "2.0",
          id: 2,
          method: "tools/list",
          params: {},
        },
      ],
      8000
    );

    const listResponse = responses.find((r: any) => r.id === 2);
    expect(listResponse?.result?.tools).toBeDefined();
    expect(Array.isArray(listResponse?.result?.tools)).toBe(true);
      expect(listResponse?.result?.tools?.length).toBe(9);
    },
    15000
  );
});
