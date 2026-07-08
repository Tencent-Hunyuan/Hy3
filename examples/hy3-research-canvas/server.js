import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join, normalize } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const rootDir = fileURLToPath(new URL(".", import.meta.url));
const publicDir = join(rootDir, "public");
const port = Number(process.env.PORT || 4173);

const contentTypes = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml"
};

export async function callHy3(messages, { reasoningEffort = "high" } = {}) {
  if (isMockMode()) {
    return mockHy3(messages);
  }

  const baseUrl = (process.env.HY3_BASE_URL || "http://127.0.0.1:8000/v1").replace(/\/$/, "");
  const apiKey = process.env.HY3_API_KEY;
  const model = process.env.HY3_MODEL || "hy3";

  if (!apiKey) {
    throw new Error("HY3_API_KEY is required unless HY3_MOCK=1 is set.");
  }

  const response = await fetch(`${baseUrl}/chat/completions`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${apiKey}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      model,
      messages,
      temperature: 0.35,
      top_p: 1,
      extra_body: {
        chat_template_kwargs: {
          reasoning_effort: reasoningEffort
        }
      }
    })
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Hy3 API returned ${response.status}: ${detail}`);
  }

  const payload = await response.json();
  return payload.choices?.[0]?.message?.content || "";
}

export function isMockMode() {
  return ["1", "true", "yes", "on"].includes(String(process.env.HY3_MOCK || "").toLowerCase());
}

export async function generateResearchBrief(input) {
  const prompt = [
    "Create a practical research brief as JSON.",
    `Topic: ${input.topic}`,
    `Audience: ${input.audience}`,
    `Depth: ${input.depth}`,
    `Known context: ${input.context || "none"}`,
    "Return fields: title, plan array, report markdown, citations array of {label,url,note}, risks array, nextActions array."
  ].join("\n");

  const content = await callHy3([
    {
      role: "system",
      content: "You are Hy3 in a product research assistant. Return concise valid JSON with grounded caveats."
    },
    { role: "user", content: prompt }
  ]);

  return parseJsonOrFallback(content, "research");
}

export async function rewriteContent(input) {
  const prompt = [
    "Rewrite the text while preserving factual claims.",
    `Target language: ${input.language}`,
    `Tone: ${input.tone}`,
    `Audience: ${input.audience}`,
    "Text:",
    input.text
  ].join("\n");

  const content = await callHy3([
    {
      role: "system",
      content: "You are Hy3 in a multilingual writing assistant. Return JSON with rewritten, rationale, and cautions."
    },
    { role: "user", content: prompt }
  ], { reasoningEffort: "no_think" });

  return parseJsonOrFallback(content, "rewrite");
}

function parseJsonOrFallback(content, type) {
  try {
    return JSON.parse(stripJsonFence(content));
  } catch {
    if (type === "rewrite") {
      return {
        rewritten: content,
        rationale: "Hy3 returned free-form text instead of JSON, so the app preserved it as the rewritten result.",
        cautions: ["Review factual claims before publishing."]
      };
    }
    return {
      title: "Hy3 Research Brief",
      plan: ["Clarify scope", "Collect evidence", "Synthesize tradeoffs"],
      report: content,
      citations: [],
      risks: ["Hy3 returned free-form text instead of JSON."],
      nextActions: ["Review the report and rerun with stricter formatting if needed."]
    };
  }
}

function stripJsonFence(content) {
  return content.trim().replace(/^```json\s*/i, "").replace(/^```\s*/i, "").replace(/\s*```$/i, "");
}

function mockHy3(messages) {
  const user = messages.at(-1)?.content || "";
  if (user.includes("Rewrite the text")) {
    return JSON.stringify({
      rewritten: "Team update: Hy3 now coordinates planning, evidence review, and final wording in one guided workflow. The release is ready for a concise bilingual launch note.",
      rationale: "The rewrite keeps the factual claims, simplifies the sentence structure, and uses a confident product-update tone.",
      cautions: ["Confirm release dates and benchmark numbers before publishing."]
    });
  }

  return JSON.stringify({
    title: "Hy3 Research Canvas: Product Research Brief",
    plan: [
      "Frame the decision and target audience.",
      "Collect first-party notes, public evidence, and measurable constraints.",
      "Use Hy3 to synthesize options, risks, and next actions."
    ],
    report: "## Executive Summary\nHy3 can act as the reasoning layer for a research assistant that turns scattered context into an actionable brief. The strongest fit is early product discovery, where teams need a plan, cited synthesis, and crisp follow-up questions.\n\n## Recommended Workflow\n1. Capture the topic, audience, depth, and known context.\n2. Ask Hy3 to produce a plan and identify evidence gaps.\n3. Review citations and export the final brief for stakeholders.\n\n## Why Hy3\nHy3's long-context and agent-oriented training make it suitable for structured synthesis, multi-step planning, and controlled writing.",
    citations: [
      {
        label: "Hy3 README",
        url: "https://github.com/Tencent-Hunyuan/Hy3",
        note: "Describes Hy3's agent, long-context, and OpenAI-compatible API capabilities."
      },
      {
        label: "Rhino-Bird Issue #4",
        url: "https://github.com/Tencent-Hunyuan/Hy3/issues/4",
        note: "Requires an end-to-end interactive application powered by Hy3."
      }
    ],
    risks: [
      "Generated citations should be checked before external publication.",
      "Live API quality depends on the configured Hy3 serving endpoint."
    ],
    nextActions: [
      "Run the app against a live Hy3 endpoint.",
      "Record the two demo flows as a short GIF or video.",
      "Add real source collection if the app is extended beyond this example."
    ]
  });
}

async function readJson(request) {
  const chunks = [];
  for await (const chunk of request) {
    chunks.push(chunk);
  }
  return JSON.parse(Buffer.concat(chunks).toString("utf-8") || "{}");
}

async function sendJson(response, status, payload) {
  response.writeHead(status, { "Content-Type": "application/json; charset=utf-8" });
  response.end(JSON.stringify(payload));
}

async function serveStatic(response, pathname) {
  const safePath = pathname === "/" ? "/index.html" : pathname;
  const filePath = normalize(join(publicDir, safePath));
  if (!filePath.startsWith(publicDir)) {
    response.writeHead(403);
    response.end("Forbidden");
    return;
  }

  try {
    const data = await readFile(filePath);
    response.writeHead(200, { "Content-Type": contentTypes[extname(filePath)] || "application/octet-stream" });
    response.end(data);
  } catch {
    response.writeHead(404);
    response.end("Not found");
  }
}

export function createAppServer() {
  return createServer(async (request, response) => {
    const url = new URL(request.url || "/", `http://${request.headers.host}`);
    try {
      if (request.method === "POST" && url.pathname === "/api/research") {
        const payload = await readJson(request);
        await sendJson(response, 200, await generateResearchBrief(payload));
        return;
      }

      if (request.method === "POST" && url.pathname === "/api/rewrite") {
        const payload = await readJson(request);
        await sendJson(response, 200, await rewriteContent(payload));
        return;
      }

      if (request.method === "GET" && url.pathname === "/api/status") {
        await sendJson(response, 200, {
          model: process.env.HY3_MODEL || "hy3",
          mock: isMockMode(),
          baseUrl: process.env.HY3_BASE_URL || "http://127.0.0.1:8000/v1"
        });
        return;
      }

      if (request.method === "GET") {
        await serveStatic(response, url.pathname);
        return;
      }

      response.writeHead(405);
      response.end("Method not allowed");
    } catch (error) {
      await sendJson(response, 500, { error: error.message });
    }
  });
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  createAppServer().listen(port, "127.0.0.1", () => {
    console.log(`Hy3 Research Canvas running at http://127.0.0.1:${port}`);
  });
}
