process.env.HY3_MOCK = process.env.HY3_MOCK || "1";

const { generateResearchBrief, rewriteContent } = await import("../server.js");

const demos = {
  async research() {
    return generateResearchBrief({
      topic: "How should a small AI team evaluate Hy3 for product research workflows?",
      audience: "Product manager and engineering lead",
      depth: "Executive brief",
      context: "The team needs repeatable plans, cited synthesis, and stakeholder-ready summaries."
    });
  },
  async rewrite() {
    return rewriteContent({
      text: "Hy3 helps the team plan research, inspect evidence, and draft a final report from the same workspace.",
      language: "English",
      tone: "Product launch",
      audience: "External developers"
    });
  }
};

const requested = process.argv[2] ? [process.argv[2]] : Object.keys(demos);

for (const name of requested) {
  if (!demos[name]) {
    throw new Error(`Unknown demo: ${name}`);
  }
  const result = await demos[name]();
  console.log(`\n# ${name}`);
  console.log(JSON.stringify(result, null, 2));
}
