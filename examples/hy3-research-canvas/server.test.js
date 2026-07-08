import test from "node:test";
import assert from "node:assert/strict";

process.env.HY3_MOCK = "1";

const { generateResearchBrief, rewriteContent } = await import("./server.js");

test("generateResearchBrief returns a structured mock brief", async () => {
  const result = await generateResearchBrief({
    topic: "Hy3 product research",
    audience: "PM",
    depth: "Executive brief",
    context: "Need an app demo"
  });

  assert.equal(result.title, "Hy3 Research Canvas: Product Research Brief");
  assert.ok(result.plan.length >= 3);
  assert.ok(result.citations[0].url.includes("Tencent-Hunyuan/Hy3"));
});

test("rewriteContent returns rewrite fields", async () => {
  const result = await rewriteContent({
    text: "Hy3 makes research easier.",
    language: "English",
    tone: "Product launch",
    audience: "Developers"
  });

  assert.match(result.rewritten, /Hy3/);
  assert.ok(result.cautions.length >= 1);
});
