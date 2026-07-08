const tabs = document.querySelectorAll(".tab");
const researchForm = document.querySelector("#researchForm");
const rewriteForm = document.querySelector("#rewriteForm");
const statusLine = document.querySelector("#statusLine");
const loading = document.querySelector("#loading");
const resultTitle = document.querySelector("#resultTitle");
const reportOutput = document.querySelector("#reportOutput");
const planOutput = document.querySelector("#planOutput");
const citationOutput = document.querySelector("#citationOutput");
const riskOutput = document.querySelector("#riskOutput");
const actionOutput = document.querySelector("#actionOutput");
const loadDemo = document.querySelector("#loadDemo");

let activeTab = "research";

tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    activeTab = tab.dataset.tab;
    tabs.forEach((item) => item.classList.toggle("active", item === tab));
    researchForm.classList.toggle("hidden", activeTab !== "research");
    rewriteForm.classList.toggle("hidden", activeTab !== "rewrite");
  });
});

researchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(researchForm);
  const payload = Object.fromEntries(form.entries());
  await runRequest("/api/research", payload, renderResearch);
});

rewriteForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(rewriteForm);
  const payload = Object.fromEntries(form.entries());
  await runRequest("/api/rewrite", payload, renderRewrite);
});

loadDemo.addEventListener("click", () => {
  if (activeTab === "research") {
    researchForm.requestSubmit();
  } else {
    rewriteForm.requestSubmit();
  }
});

async function runRequest(path, payload, renderer) {
  loading.classList.remove("hidden");
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
    renderer(data);
  } catch (error) {
    resultTitle.textContent = "Request failed";
    reportOutput.innerHTML = `<p>${escapeHtml(error.message)}</p>`;
    planOutput.replaceChildren();
    citationOutput.replaceChildren();
    riskOutput.replaceChildren();
    actionOutput.replaceChildren();
  } finally {
    loading.classList.add("hidden");
  }
}

function renderResearch(data) {
  resultTitle.textContent = data.title || "Hy3 Research Brief";
  reportOutput.innerHTML = markdownToHtml(data.report || "");
  renderList(planOutput, data.plan || []);
  renderCitations(data.citations || []);
  renderList(riskOutput, data.risks || []);
  renderList(actionOutput, data.nextActions || []);
}

function renderRewrite(data) {
  resultTitle.textContent = "Hy3 Rewrite Result";
  reportOutput.innerHTML = `<p>${escapeHtml(data.rewritten || "")}</p>`;
  renderList(planOutput, ["Preserve factual claims", "Adapt target language", "Tune tone for the selected audience"]);
  renderCitations([]);
  renderList(riskOutput, data.cautions || []);
  renderList(actionOutput, [data.rationale || "Review and publish the rewritten text."]);
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
    item.append(link, note);
    citationOutput.append(item);
  });
}

function markdownToHtml(markdown) {
  return escapeHtml(markdown)
    .split("\n")
    .map((line) => {
      if (line.startsWith("## ")) {
        return `<h2>${line.slice(3)}</h2>`;
      }
      if (/^\d+\.\s/.test(line)) {
        return `<p>${line}</p>`;
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
      ? `Mock mode using ${status.model}`
      : `Live Hy3 endpoint: ${status.baseUrl}`;
  })
  .catch(() => {
    statusLine.textContent = "Status unavailable";
  });
