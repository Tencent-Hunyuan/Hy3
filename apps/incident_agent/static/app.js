"use strict";

const state = {
  demos: [],
  files: [],
  controller: null,
  report: "",
  toolCards: new Map(),
};

const elements = {
  statusDot: document.getElementById("status-dot"),
  statusLabel: document.getElementById("status-label"),
  modelLabel: document.getElementById("model-label"),
  demoSelect: document.getElementById("demo-select"),
  taskInput: document.getElementById("task-input"),
  taskCount: document.getElementById("task-count"),
  fileInput: document.getElementById("file-input"),
  filePicker: document.querySelector(".file-picker"),
  fileList: document.getElementById("file-list"),
  runButton: document.getElementById("run-button"),
  cancelButton: document.getElementById("cancel-button"),
  copyButton: document.getElementById("copy-button"),
  timeline: document.getElementById("timeline"),
};

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

async function loadDemos() {
  try {
    const response = await fetch("/api/demos");
    if (!response.ok) throw new Error("Demos unavailable");
    state.demos = await response.json();
    state.demos.forEach((demo) => {
      const option = document.createElement("option");
      option.value = demo.id;
      option.textContent = demo.title;
      elements.demoSelect.append(option);
    });
  } catch (error) {
    const option = document.createElement("option");
    option.disabled = true;
    option.textContent = "Demos unavailable";
    elements.demoSelect.append(option);
  }
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  return `${(bytes / 1024).toFixed(1)} KiB`;
}

function renderFiles() {
  elements.fileList.replaceChildren();
  if (elements.demoSelect.value) {
    const item = document.createElement("li");
    item.textContent = "Built-in evidence bundle";
    elements.fileList.append(item);
    return;
  }
  if (!state.files.length) {
    const item = document.createElement("li");
    item.className = "file-placeholder";
    item.textContent = "No evidence selected";
    elements.fileList.append(item);
    return;
  }
  state.files.forEach((file) => {
    const item = document.createElement("li");
    item.textContent = `${file.name} / ${formatBytes(file.size)}`;
    item.title = file.name;
    elements.fileList.append(item);
  });
}

function updateTaskCount() {
  elements.taskCount.textContent = `${elements.taskInput.value.length.toLocaleString()} / 2,000`;
}

function selectDemo() {
  const demo = state.demos.find((item) => item.id === elements.demoSelect.value);
  const hasDemo = Boolean(demo);
  if (demo) {
    elements.taskInput.value = demo.task;
    state.files = [];
    elements.fileInput.value = "";
  }
  elements.fileInput.disabled = hasDemo;
  elements.filePicker.classList.toggle("is-disabled", hasDemo);
  updateTaskCount();
  renderFiles();
}

function selectFiles() {
  state.files = [...elements.fileInput.files];
  if (state.files.length) elements.demoSelect.value = "";
  elements.fileInput.disabled = false;
  elements.filePicker.classList.remove("is-disabled");
  renderFiles();
}

function setRunning(running) {
  elements.runButton.disabled = running;
  elements.cancelButton.disabled = !running;
  elements.demoSelect.disabled = running;
  elements.taskInput.disabled = running;
  elements.fileInput.disabled = running || Boolean(elements.demoSelect.value);
  elements.filePicker.classList.toggle(
    "is-disabled",
    running || Boolean(elements.demoSelect.value),
  );
  elements.runButton.textContent = running ? "Investigating..." : "Start investigation";
}

function clearTimeline() {
  elements.timeline.replaceChildren();
  state.toolCards.clear();
  state.report = "";
  elements.copyButton.disabled = true;
}

function eventCard(title, status, className = "") {
  const card = document.createElement("article");
  card.className = `event-card ${className}`.trim();
  const heading = document.createElement("div");
  heading.className = "event-heading";
  const strong = document.createElement("strong");
  strong.textContent = title;
  const statusLabel = document.createElement("span");
  statusLabel.className = "event-status";
  statusLabel.textContent = status;
  heading.append(strong, statusLabel);
  card.append(heading);
  elements.timeline.append(card);
  return { card, statusLabel };
}

function appendTextEvent(title, content, className, status = "complete") {
  const { card } = eventCard(title, status, className);
  const paragraph = document.createElement("p");
  paragraph.textContent = content;
  card.append(paragraph);
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
  let listType = "";
  const closeList = () => {
    if (listType) output.push(`</${listType}>`);
    listType = "";
  };
  lines.forEach((line) => {
    if (!line.trim()) {
      closeList();
      return;
    }
    const heading = line.match(/^(#{1,3})\s+(.+)$/);
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
  return output.join("");
}

function renderEvent(event) {
  if (event.type === "started") {
    appendTextEvent(
      "Investigation started",
      `Hy3 can use up to ${event.max_rounds} evidence rounds.`,
      "is-running",
      "running",
    );
    return;
  }
  if (event.type === "plan") {
    appendTextEvent("Hy3 plan", event.content, "is-success");
    return;
  }
  if (event.type === "tool_call") {
    const { card, statusLabel } = eventCard(event.tool, "running", "is-running");
    const pre = document.createElement("pre");
    pre.textContent = JSON.stringify(event.arguments, null, 2);
    card.append(pre);
    state.toolCards.set(event.call_id, { card, statusLabel });
    return;
  }
  if (event.type === "tool_result") {
    const tracked = state.toolCards.get(event.call_id);
    if (!tracked) return;
    tracked.card.classList.remove("is-running");
    tracked.card.classList.add(event.ok ? "is-success" : "is-error");
    tracked.statusLabel.textContent = event.ok ? "complete" : "failed";
    const details = document.createElement("details");
    const summary = document.createElement("summary");
    summary.textContent = "Observation";
    const pre = document.createElement("pre");
    pre.textContent = event.content;
    details.append(summary, pre);
    tracked.card.append(details);
    return;
  }
  if (event.type === "report") {
    state.report = event.content;
    const { card } = eventCard("Incident report", "final", "is-report");
    const report = document.createElement("div");
    report.className = "report-content";
    report.innerHTML = renderMarkdown(event.content);
    card.append(report);
    elements.copyButton.disabled = false;
    return;
  }
  if (event.type === "error") {
    appendTextEvent("Investigation error", event.message, "is-error", "error");
  }
}

async function readEventStream(response, onEvent) {
  if (!response.body) throw new Error("Streaming response is unavailable.");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";
    lines.filter(Boolean).forEach((line) => onEvent(JSON.parse(line)));
    if (done) break;
  }
  if (buffer.trim()) onEvent(JSON.parse(buffer));
}

async function responseError(response) {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
  } catch (error) {
    // The fallback below is intentionally generic.
  }
  return "The investigation request failed.";
}

async function startInvestigation() {
  const task = elements.taskInput.value.trim();
  if (!task) {
    clearTimeline();
    appendTextEvent("Input required", "Describe the incident before starting.", "is-error", "error");
    return;
  }
  if (!elements.demoSelect.value && !state.files.length) {
    clearTimeline();
    appendTextEvent("Evidence required", "Choose a demo or select evidence files.", "is-error", "error");
    return;
  }

  const form = new FormData();
  form.append("task", task);
  if (elements.demoSelect.value) {
    form.append("demo_id", elements.demoSelect.value);
  } else {
    state.files.forEach((file) => form.append("files", file, file.name));
  }

  clearTimeline();
  state.controller = new AbortController();
  setRunning(true);
  try {
    const response = await fetch("/api/investigate", {
      method: "POST",
      body: form,
      signal: state.controller.signal,
    });
    if (!response.ok) throw new Error(await responseError(response));
    await readEventStream(response, renderEvent);
  } catch (error) {
    if (error.name === "AbortError") {
      appendTextEvent("Investigation canceled", "The completed evidence trace was preserved.", "is-error", "canceled");
    } else {
      appendTextEvent("Request failed", error.message || "The investigation request failed.", "is-error", "error");
    }
  } finally {
    state.controller = null;
    setRunning(false);
  }
}

function cancelInvestigation() {
  state.controller?.abort();
}

async function copyReport() {
  if (!state.report) return;
  try {
    await navigator.clipboard.writeText(state.report);
    elements.copyButton.textContent = "Copied";
    window.setTimeout(() => { elements.copyButton.textContent = "Copy report"; }, 1200);
  } catch (error) {
    appendTextEvent("Clipboard unavailable", "Copy the report manually from the timeline.", "is-error", "error");
  }
}

elements.demoSelect.addEventListener("change", selectDemo);
elements.taskInput.addEventListener("input", updateTaskCount);
elements.fileInput.addEventListener("change", selectFiles);
elements.runButton.addEventListener("click", startInvestigation);
elements.cancelButton.addEventListener("click", cancelInvestigation);
elements.copyButton.addEventListener("click", copyReport);

document.addEventListener("DOMContentLoaded", async () => {
  updateTaskCount();
  renderFiles();
  await Promise.all([loadStatus(), loadDemos()]);
});
