const tabs = document.querySelectorAll(".tab");
const researchForm = document.querySelector("#researchForm");
const rewriteForm = document.querySelector("#rewriteForm");
const statusLine = document.querySelector("#statusLine");
const loading = document.querySelector("#loading");
const resultTitle = document.querySelector("#resultTitle");
const reportOutput = document.querySelector("#reportOutput");
const planOutput = document.querySelector("#planOutput");
const traceOutput = document.querySelector("#traceOutput");
const citationOutput = document.querySelector("#citationOutput");
const riskOutput = document.querySelector("#riskOutput");
const actionOutput = document.querySelector("#actionOutput");
const summaryStrip = document.querySelector("#summaryStrip");
const confidencePill = document.querySelector("#confidencePill");
const loadDemo = document.querySelector("#loadDemo");
const copyMarkdown = document.querySelector("#copyMarkdown");
const exportJson = document.querySelector("#exportJson");
const actionToast = document.querySelector("#actionToast");
const modeInputs = document.querySelectorAll("input[name='thinkingMode']");
const seedButtons = document.querySelectorAll(".seed-button");

const seeds = {
  product: {
    tab: "research",
    mode: "deep",
    topic: "How should a small AI team evaluate Hy3 for product research workflows?",
    audience: "Product manager and engineering lead",
    depth: "Executive brief",
    context: "The team needs a repeatable way to turn notes into cited plans and stakeholder-ready summaries."
  },
  release: {
    tab: "rewrite",
    mode: "fast",
    text: "Hy3 helps the team plan research, inspect evidence, and draft a final report from the same workspace.",
    language: "English",
    tone: "Product launch",
    audience: "External developers"
  }
};

let activeTab = "research";
let latestResult = null;

tabs.forEach((tab) => {
  tab.addEventListener("click", () => switchTab(tab.dataset.tab));
});

seedButtons.forEach((button) => {
  button.addEventListener("click", () => applySeed(button.dataset.seed));
});

researchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(researchForm);
  const payload = {
    ...Object.fromEntries(form.entries()),
    thinkingMode: selectedThinkingMode()
  };
  await runRequest("/api/research", payload, renderResearch);
});

rewriteForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(rewriteForm);
  const payload = {
    ...Object.fromEntries(form.entries()),
    thinkingMode: selectedThinkingMode()
  };
  await runRequest("/api/rewrite", payload, renderRewrite);
});

loadDemo.addEventListener("click", () => {
  if (activeTab === "research") {
    applySeed("product");
    researchForm.requestSubmit();
  } else {
    applySeed("release");
    rewriteForm.requestSubmit();
  }
});

copyMarkdown.addEventListener("click", async () => {
  const markdown = latestResult?.report || latestResult?.rewritten || reportOutput.innerText;
  await copyText(markdown);
  showToast("Copied current Hy3 output as Markdown.");
  flashButton(copyMarkdown, "Copied");
});

exportJson.addEventListener("click", () => {
  const data = JSON.stringify(latestResult || {}, null, 2);
  const blob = new Blob([data], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "hy3-research-canvas-result.json";
  link.hidden = true;
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  showToast("Exported current Hy3 result as JSON.");
  flashButton(exportJson, "Exported");
});

function switchTab(tabName) {
  activeTab = tabName;
  tabs.forEach((item) => item.classList.toggle("active", item.dataset.tab === tabName));
  researchForm.classList.toggle("hidden", activeTab !== "research");
  rewriteForm.classList.toggle("hidden", activeTab !== "rewrite");
}

function applySeed(seedName) {
  const seed = seeds[seedName];
  if (!seed) return;
  switchTab(seed.tab);
  setThinkingMode(seed.mode);
  const form = seed.tab === "research" ? researchForm : rewriteForm;
  Object.entries(seed).forEach(([key, value]) => {
    const field = form.elements.namedItem(key);
    if (field) field.value = value;
  });
}

async function runRequest(path, payload, renderer) {
  loading.classList.remove("hidden");
  setControlsDisabled(true);
  try {
    const response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Request failed");
    }
    latestResult = data;
    renderer(data);
  } catch (error) {
    latestResult = { error: error.message };
    resultTitle.textContent = "Request failed";
    reportOutput.innerHTML = `<p>${escapeHtml(error.message)}</p>`;
    planOutput.replaceChildren();
    traceOutput.replaceChildren();
    citationOutput.replaceChildren();
    riskOutput.replaceChildren();
    actionOutput.replaceChildren();
    summaryStrip.replaceChildren();
    confidencePill.textContent = "Error";
  } finally {
    setControlsDisabled(false);
    loading.classList.add("hidden");
  }
}

function renderResearch(data) {
  resultTitle.textContent = data.title || "Hy3 Research Brief";
  reportOutput.innerHTML = markdownToHtml(data.report || "");
  confidencePill.textContent = `${labelMode(data.thinkingMode)} mode · ${data.confidence || "Medium"} confidence`;
  renderSummary(data.summaryCards || []);
  renderTrace(data.trace || []);
  renderList(planOutput, data.plan || []);
  renderCitations(data.citations || []);
  renderList(riskOutput, data.risks || []);
  renderList(actionOutput, data.nextActions || []);
}

function renderRewrite(data) {
  resultTitle.textContent = "Hy3 Rewrite Result";
  reportOutput.innerHTML = `<p>${escapeHtml(data.rewritten || "")}</p>`;
  confidencePill.textContent = `${labelMode(data.thinkingMode)} mode · ${data.confidence || "Medium"} confidence`;
  renderSummary([
    { label: "Mode", value: labelMode(data.thinkingMode), note: "Controls Hy3 reasoning effort." },
    { label: "Tone", value: rewriteForm.elements.namedItem("tone").value, note: "Selected rewrite voice." },
    { label: "Language", value: rewriteForm.elements.namedItem("language").value, note: "Target output language." }
  ]);
  renderTrace(data.trace || []);
  renderList(planOutput, ["Preserve factual claims", "Adapt target language", "Tune tone for the selected audience"]);
  renderCitations([]);
  renderList(riskOutput, data.cautions || []);
  renderList(actionOutput, [data.rationale || "Review and publish the rewritten text."]);
}

function renderSummary(cards) {
  summaryStrip.replaceChildren();
  cards.forEach((card) => {
    const item = document.createElement("div");
    item.className = "summary-card";
    item.innerHTML = `
      <span>${escapeHtml(card.label || "")}</span>
      <strong>${escapeHtml(card.value || "")}</strong>
      <p>${escapeHtml(card.note || "")}</p>
    `;
    summaryStrip.append(item);
  });
}

function renderTrace(items) {
  traceOutput.replaceChildren();
  items.forEach((item) => {
    const li = document.createElement("li");
    li.innerHTML = `
      <div>
        <strong>${escapeHtml(item.stage || "Stage")}</strong>
        <p>${escapeHtml(item.note || "")}</p>
      </div>
      <span>${escapeHtml(item.status || "Done")}</span>
    `;
    traceOutput.append(li);
  });
}

function renderList(node, items) {
  node.replaceChildren();
  items.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    node.append(li);
  });
}

function renderCitations(citations) {
  citationOutput.replaceChildren();
  if (!citations.length) {
    const empty = document.createElement("p");
    empty.className = "empty-note";
    empty.textContent = "No citations returned for this workflow.";
    citationOutput.append(empty);
    return;
  }

  citations.forEach((citation) => {
    const item = document.createElement("div");
    item.className = "citation";
    const link = document.createElement("a");
    link.href = citation.url || "#";
    link.target = "_blank";
    link.rel = "noreferrer";
    link.textContent = citation.label || citation.url || "Source";
    const note = document.createElement("p");
    note.textContent = citation.note || "";
    const confidence = document.createElement("span");
    confidence.className = "source-confidence";
    confidence.textContent = citation.confidence || "Review";
    item.append(link, confidence, note);
    citationOutput.append(item);
  });
}

function selectedThinkingMode() {
  return [...modeInputs].find((item) => item.checked)?.value || "deep";
}

function setThinkingMode(mode) {
  modeInputs.forEach((input) => {
    input.checked = input.value === mode;
  });
}

function labelMode(mode) {
  return mode === "fast" ? "Fast" : "Deep";
}

function setControlsDisabled(disabled) {
  document.querySelectorAll("button, input, textarea, select").forEach((control) => {
    control.disabled = disabled;
  });
}

async function copyText(text) {
  if (navigator.clipboard?.writeText) {
    try {
      await Promise.race([
        navigator.clipboard.writeText(text),
        new Promise((_, reject) => {
          window.setTimeout(() => reject(new Error("Clipboard write timed out")), 600);
        })
      ]);
      return;
    } catch {
      // Fall through to the textarea path for browser environments that block clipboard writes.
    }
  }
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.append(textarea);
  textarea.select();
  document.execCommand("copy");
  textarea.remove();
}

function showToast(message) {
  actionToast.textContent = message;
  actionToast.classList.remove("hidden");
  window.setTimeout(() => {
    actionToast.classList.add("hidden");
  }, 2200);
}

function flashButton(button, text) {
  const original = button.textContent;
  button.textContent = text;
  window.setTimeout(() => {
    button.textContent = original;
  }, 1200);
}

function markdownToHtml(markdown) {
  return escapeHtml(markdown)
    .split("\n")
    .map((line) => {
      if (line.startsWith("## ")) {
        return `<h2>${line.slice(3)}</h2>`;
      }
      if (/^\d+\.\s/.test(line)) {
        return `<p class="numbered-line">${line}</p>`;
      }
      return line.trim() ? `<p>${line}</p>` : "";
    })
    .join("");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

fetch("/api/status")
  .then((response) => response.json())
  .then((status) => {
    statusLine.textContent = status.mock
      ? `Mock mode · ${status.model}`
      : `Live Hy3 endpoint · ${status.baseUrl}`;
  })
  .catch(() => {
    statusLine.textContent = "Status unavailable";
  });
