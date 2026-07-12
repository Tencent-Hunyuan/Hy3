"use strict";

const state = {
  mode: "review",
  examples: [],
  lastResult: "",
};

const elements = {
  statusDot: document.getElementById("status-dot"),
  statusLabel: document.getElementById("status-label"),
  modelLabel: document.getElementById("model-label"),
  modeButtons: [...document.querySelectorAll(".mode-button")],
  reviewFields: [...document.querySelectorAll(".review-field")],
  testFields: [...document.querySelectorAll(".test-field")],
  exampleSelect: document.getElementById("example-select"),
  languageInput: document.getElementById("language-input"),
  focusSelect: document.getElementById("focus-select"),
  frameworkInput: document.getElementById("framework-input"),
  riskSelect: document.getElementById("risk-select"),
  contextInput: document.getElementById("context-input"),
  diffInput: document.getElementById("diff-input"),
  charCount: document.getElementById("char-count"),
  runButton: document.getElementById("run-button"),
  copyButton: document.getElementById("copy-button"),
  result: document.getElementById("result"),
  resultMeta: document.getElementById("result-meta"),
};

function setMode(mode) {
  state.mode = mode === "tests" ? "tests" : "review";
  const isReview = state.mode === "review";
  elements.modeButtons.forEach((button) => {
    const isActive = button.dataset.mode === state.mode;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-selected", String(isActive));
  });
  elements.reviewFields.forEach((field) => { field.hidden = !isReview; });
  elements.testFields.forEach((field) => { field.hidden = isReview; });
  elements.runButton.textContent = isReview ? "Run Hy3 review" : "Build test plan";
}

function updateCount() {
  elements.charCount.textContent = `${elements.diffInput.value.length.toLocaleString()} / 24,000`;
}

function loadExample(id) {
  const example = state.examples.find((item) => item.id === id);
  if (!example) return;
  setMode(example.mode);
  elements.languageInput.value = example.language;
  elements.frameworkInput.value = example.framework;
  elements.riskSelect.value = example.risk_level;
  elements.contextInput.value = example.context;
  elements.diffInput.value = example.diff_text;
  updateCount();
}

async function loadStatus() {
  try {
    const response = await fetch("/api/status");
    if (!response.ok) throw new Error("Status unavailable");
    const status = await response.json();
    elements.statusDot.classList.toggle("is-ready", status.ready);
    elements.statusDot.classList.toggle("is-error", !status.ready);
    elements.statusLabel.textContent = status.ready ? "Hy3 connected" : "Setup required";
    elements.modelLabel.textContent = status.model;
    elements.modelLabel.title = status.endpoint;
  } catch (error) {
    elements.statusDot.classList.add("is-error");
    elements.statusLabel.textContent = "Status unavailable";
  }
}

async function loadExamples() {
  try {
    const response = await fetch("/api/examples");
    if (!response.ok) throw new Error("Examples unavailable");
    state.examples = await response.json();
    state.examples.forEach((example) => {
      const option = document.createElement("option");
      option.value = example.id;
      option.textContent = example.title;
      elements.exampleSelect.append(option);
    });
  } catch (error) {
    const option = document.createElement("option");
    option.textContent = "Examples unavailable";
    option.disabled = true;
    elements.exampleSelect.append(option);
  }
}

function reviewPayload(diff) {
  return {
    patch_text: diff,
    language: elements.languageInput.value.trim() || "unknown",
    focus: elements.focusSelect.value,
    context: elements.contextInput.value.trim(),
  };
}

function testPayload(diff) {
  return {
    diff_text: diff,
    test_framework: elements.frameworkInput.value.trim() || "unknown",
    risk_level: elements.riskSelect.value,
  };
}

function errorMessage(body) {
  if (typeof body.detail === "string") return body.detail;
  if (Array.isArray(body.detail) && body.detail[0]?.msg) return body.detail[0].msg;
  return "The request failed. Try again.";
}

function escapeHtml(value) {
  return value.replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#039;",
  })[character]);
}

function inlineFormat(value) {
  return value
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
}

function renderMarkdown(text) {
  const lines = escapeHtml(text).split("\n");
  const output = [];
  let inCode = false;
  let listType = "";

  const closeList = () => {
    if (listType) output.push(`</${listType}>`);
    listType = "";
  };

  lines.forEach((line) => {
    if (line.startsWith("```")) {
      closeList();
      output.push(inCode ? "</code></pre>" : "<pre><code>");
      inCode = !inCode;
      return;
    }
    if (inCode) {
      output.push(`${line}\n`);
      return;
    }
    if (!line.trim()) {
      closeList();
      return;
    }

    const heading = line.match(/^(#{1,4})\s+(.+)$/);
    if (heading) {
      closeList();
      const level = heading[1].length;
      output.push(`<h${level}>${inlineFormat(heading[2])}</h${level}>`);
      return;
    }

    const unordered = line.match(/^\s*[-*]\s+(.+)$/);
    const ordered = line.match(/^\s*\d+[.)]\s+(.+)$/);
    if (unordered || ordered) {
      const nextType = unordered ? "ul" : "ol";
      if (listType !== nextType) {
        closeList();
        listType = nextType;
        output.push(`<${listType}>`);
      }
      output.push(`<li>${inlineFormat((unordered || ordered)[1])}</li>`);
      return;
    }

    closeList();
    output.push(`<p>${inlineFormat(line)}</p>`);
  });

  closeList();
  if (inCode) output.push("</code></pre>");
  return output.join("");
}

function renderMetadata(metadata) {
  elements.resultMeta.replaceChildren();
  const entries = [
    metadata.language || metadata.test_framework,
    metadata.focus || metadata.risk_level,
    `${Number(metadata.diff_chars || 0).toLocaleString()} chars`,
    `${Number(metadata.duration_ms || 0).toLocaleString()} ms`,
  ].filter(Boolean);
  entries.forEach((value) => {
    const chip = document.createElement("span");
    chip.className = "meta-chip";
    chip.textContent = value;
    elements.resultMeta.append(chip);
  });
}

function renderResult(content, metadata) {
  elements.result.innerHTML = `<div class="result-content">${renderMarkdown(content)}</div>`;
  renderMetadata(metadata);
  elements.copyButton.disabled = false;
}

function showError(message) {
  elements.resultMeta.replaceChildren();
  elements.result.innerHTML = "";
  const error = document.createElement("div");
  error.className = "error-state";
  const title = document.createElement("strong");
  title.textContent = "Analysis unavailable";
  const detail = document.createElement("p");
  detail.textContent = message;
  error.append(title, detail);
  elements.result.append(error);
  elements.copyButton.disabled = true;
}

function setLoading(isLoading) {
  elements.runButton.disabled = isLoading;
  if (isLoading) {
    elements.runButton.textContent = "Analyzing...";
    elements.resultMeta.replaceChildren();
    elements.result.innerHTML = '<div class="loading-state"><div class="loading-bar"></div><p>Hy3 is reviewing the change set.</p></div>';
    elements.copyButton.disabled = true;
  } else {
    elements.runButton.textContent = state.mode === "review" ? "Run Hy3 review" : "Build test plan";
  }
}

async function submitAnalysis() {
  const diff = elements.diffInput.value.trim();
  if (!diff) {
    showError("Paste a diff or load an example first.");
    return;
  }

  setLoading(true);
  try {
    const isReview = state.mode === "review";
    const response = await fetch(isReview ? "/api/review" : "/api/tests", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(isReview ? reviewPayload(diff) : testPayload(diff)),
    });
    const body = await response.json();
    if (!response.ok) throw new Error(errorMessage(body));
    state.lastResult = body.content;
    renderResult(body.content, body.metadata);
  } catch (error) {
    showError(error.message || "The request failed. Try again.");
  } finally {
    setLoading(false);
  }
}

async function copyResult() {
  if (!state.lastResult) return;
  try {
    await navigator.clipboard.writeText(state.lastResult);
    elements.copyButton.textContent = "Copied";
    window.setTimeout(() => { elements.copyButton.textContent = "Copy"; }, 1200);
  } catch (error) {
    showError("Clipboard access was denied.");
  }
}

elements.modeButtons.forEach((button) => {
  button.addEventListener("click", () => setMode(button.dataset.mode));
});
elements.exampleSelect.addEventListener("change", () => loadExample(elements.exampleSelect.value));
elements.diffInput.addEventListener("input", updateCount);
elements.runButton.addEventListener("click", submitAnalysis);
elements.copyButton.addEventListener("click", copyResult);
document.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") submitAnalysis();
});

document.addEventListener("DOMContentLoaded", async () => {
  setMode("review");
  updateCount();
  await Promise.all([loadStatus(), loadExamples()]);
});
