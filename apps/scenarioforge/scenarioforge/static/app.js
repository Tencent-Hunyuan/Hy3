const state = { examples: [], selected: null, result: null, mode: "loading" };

const $ = (id) => document.getElementById(id);
const text = (tag, value, className) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  node.textContent = value;
  return node;
};

async function getJson(url, options) {
  const response = await fetch(url, options);
  const body = await response.json().catch(() => ({ error: "服务器返回了无效 JSON" }));
  if (!response.ok) throw new Error(body.error || `请求失败 (${response.status})`);
  return body;
}

async function bootstrap() {
  try {
    const [health, examples] = await Promise.all([getJson("/api/health"), getJson("/api/examples")]);
    state.mode = health.mode;
    state.examples = examples.examples;
    renderMode(health);
    renderExamples();
    selectExample(state.examples[0].id);
  } catch (error) {
    showNotice(error.message);
    $("modeBadge").textContent = "连接失败";
  }
}

function renderMode(health) {
  const badge = $("modeBadge");
  badge.className = `mode-badge ${health.mode}`;
  badge.textContent = health.mode === "demo" ? "离线样例 · 非 Hy3 输出" : `在线 Hy3 · ${health.model}`;
  if (health.mode === "live" && !health.live_ready) {
    badge.className = "mode-badge demo";
    badge.textContent = "等待 HY3_API_KEY";
    showNotice("当前未配置 API Key。可设置 Hy3 凭据，或用 SCENARIOFORGE_DEMO_MODE=1 查看离线样例。", false);
  }
}

function renderExamples() {
  const list = $("exampleList");
  list.replaceChildren();
  state.examples.forEach((example, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "example-card";
    button.dataset.id = example.id;
    button.append(text("small", `FLOW 0${index + 1} · ${example.label}`));
    button.append(text("strong", example.title));
    button.addEventListener("click", () => selectExample(example.id));
    list.append(button);
  });
}

function selectExample(id) {
  const example = state.examples.find((item) => item.id === id);
  if (!example) return;
  state.selected = example;
  document.querySelectorAll(".example-card").forEach((card) => {
    card.classList.toggle("active", card.dataset.id === id);
  });
  $("title").value = example.title;
  $("goal").value = example.goal;
  $("plan").value = example.plan;
  $("constraints").value = example.constraints.join("\n");
  $("results").hidden = true;
  hideNotice();
}

$("rehearsalForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  hideNotice();
  const constraints = $("constraints").value.split("\n").map((item) => item.trim()).filter(Boolean);
  const payload = {
    title: $("title").value,
    goal: $("goal").value,
    plan: $("plan").value,
    constraints,
    example_id: state.selected?.id || null,
  };
  setBusy(true);
  try {
    const result = await getJson("/api/rehearse", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    state.result = result;
    renderResult(result, payload.title);
  } catch (error) {
    showNotice(error.message);
  } finally {
    setBusy(false);
  }
});

function setBusy(busy) {
  $("runButton").disabled = busy;
  $("runButton").querySelector("span").textContent = busy ? "Hy3 正在演练…" : "开始压力测试";
  $("progressPanel").hidden = !busy;
  if (busy) {
    $("results").hidden = true;
    $("progressPanel").scrollIntoView({ behavior: "smooth", block: "center" });
  }
}

function renderResult(result, titleValue) {
  $("resultTitle").textContent = titleValue;
  $("recommendation").textContent = verdictLabel(result.decision.recommendation);
  $("rationale").textContent = result.decision.rationale;
  $("objective").textContent = result.analysis.brief.objective;
  fillList("nonNegotiables", result.analysis.brief.non_negotiables);
  fillList("assumptions", result.analysis.brief.assumptions);
  fillList("nextActions", result.decision.next_48h);
  fillList("stopConditions", result.decision.stop_conditions);
  renderPerspectives(result.analysis.perspectives);
  renderScenarios(result.analysis.scenarios);
  renderGates(result.decision.gates);
  renderProvider(result);
  $("results").hidden = false;
  $("results").scrollIntoView({ behavior: "smooth", block: "start" });
}

function fillList(id, items) {
  const list = $(id);
  list.replaceChildren(...items.map((item) => text("li", item)));
}

function renderPerspectives(items) {
  const root = $("perspectives");
  root.replaceChildren(...items.map((item) => {
    const card = document.createElement("section");
    card.className = `perspective ${item.severity}`;
    const header = document.createElement("header");
    header.append(text("h4", item.name), text("span", severityLabel(item.severity), "severity"));
    card.append(header, text("p", item.concern), text("small", `计划证据：${item.evidence_from_plan}`));
    return card;
  }));
}

function renderScenarios(items) {
  const root = $("scenarios");
  root.replaceChildren(...items.map((item) => {
    const card = document.createElement("section");
    card.className = "scenario";
    const left = document.createElement("div");
    left.append(text("h4", item.title), labelled("触发", item.trigger), labelled("信号", item.early_signal));
    const right = document.createElement("div");
    right.append(labelled("影响", item.impact), labelled("响应", item.response));
    card.append(left, right);
    return card;
  }));
}

function renderGates(items) {
  const root = $("gates");
  root.replaceChildren(...items.map((item) => {
    const row = document.createElement("section");
    row.className = "gate";
    row.append(gateCell("放行条件", item.condition), gateCell("负责人", item.owner), gateCell("期限", item.deadline), gateCell("未通过时", item.fallback));
    return row;
  }));
}

function labelled(label, value) {
  const node = document.createElement("p");
  node.append(text("strong", `${label}：`), document.createTextNode(value));
  return node;
}

function gateCell(label, value) {
  const node = document.createElement("div");
  node.append(text("span", label), text("strong", value));
  return node;
}

function renderProvider(result) {
  const meta = $("providerMeta");
  meta.replaceChildren();
  meta.append(text("strong", result.mode === "live" ? "LIVE MODEL EVIDENCE" : "OFFLINE WALKTHROUGH"));
  meta.append(text("div", `provider: ${result.provider.name}`));
  meta.append(text("div", `model: ${result.provider.model}`));
  meta.append(text("div", `api calls: ${result.provider.calls}`));
  meta.append(text("div", `input: ${result.input_digest}`));
}

function verdictLabel(value) {
  return { GO: "GO · 可以执行", CONDITIONAL_GO: "CONDITIONAL · 有条件执行", NO_GO: "NO-GO · 暂停执行" }[value] || value;
}

function severityLabel(value) {
  return { low: "低", medium: "中", high: "高", critical: "致命" }[value] || value;
}

function showNotice(message, scroll = true) {
  const notice = $("formNotice");
  notice.textContent = message;
  notice.hidden = false;
  if (scroll) notice.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function hideNotice() { $("formNotice").hidden = true; }

$("exportButton").addEventListener("click", () => {
  if (!state.result) return;
  const blob = new Blob([JSON.stringify(state.result, null, 2)], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `scenarioforge-${state.result.input_digest}.json`;
  link.click();
  URL.revokeObjectURL(link.href);
});

bootstrap();
