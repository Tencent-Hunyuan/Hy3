const question = document.querySelector('#question');
const counter = document.querySelector('#counter');
const button = document.querySelector('#submitButton');
const statusBox = document.querySelector('#status');
const results = document.querySelector('#results');
const answer = document.querySelector('#answer');
const trace = document.querySelector('#trace');
const sources = document.querySelector('#sources');
const modeBadge = document.querySelector('#modeBadge');
const offlineNotice = document.querySelector('#offlineNotice');

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
  })[char]);
}

function renderMarkdown(value) {
  const safe = escapeHtml(value);
  const lines = safe.split('\n');
  let inList = false;
  const rendered = [];
  for (const line of lines) {
    if (line.startsWith('## ')) {
      if (inList) { rendered.push('</ul>'); inList = false; }
      rendered.push(`<h2>${line.slice(3)}</h2>`);
    } else if (line.startsWith('&gt; ')) {
      if (inList) { rendered.push('</ul>'); inList = false; }
      rendered.push(`<blockquote>${line.slice(5)}</blockquote>`);
    } else if (line.startsWith('- ')) {
      if (!inList) { rendered.push('<ul>'); inList = true; }
      rendered.push(`<li>${line.slice(2).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')}</li>`);
    } else if (line.trim()) {
      if (inList) { rendered.push('</ul>'); inList = false; }
      rendered.push(`<p>${line.replace(/`(.+?)`/g, '<code>$1</code>')}</p>`);
    }
  }
  if (inList) rendered.push('</ul>');
  return rendered.join('');
}

function updateCounter() {
  counter.textContent = `${question.value.length} / 500`;
}

async function loadHealth() {
  try {
    const response = await fetch('/api/health', {cache: 'no-store'});
    const data = await response.json();
    const isDemo = data.mode === 'demo';
    modeBadge.textContent = isDemo ? 'Offline Demo · 未调用 Hy3' : `Live Hy3 · ${data.model}`;
    modeBadge.className = `mode-badge ${isDemo ? 'demo' : 'live'}`;
    offlineNotice.classList.toggle('hidden', !isDemo);
  } catch (error) {
    modeBadge.textContent = 'Service unavailable';
    modeBadge.className = 'mode-badge pending';
  }
}

function renderResult(data) {
  answer.innerHTML = renderMarkdown(data.answer);
  trace.innerHTML = data.trace.map(item => `
    <li><strong>${escapeHtml(item.tool)}</strong>
      Round ${item.round} · ${item.result_count} sources<br>${escapeHtml(item.query)}
    </li>`).join('');
  sources.innerHTML = data.evidence.map(item => `
    <article class="source-item">
      <span class="source-id">[${escapeHtml(item.id)}]</span>
      <a href="${escapeHtml(item.url || '#')}" target="_blank" rel="noreferrer">${escapeHtml(item.title)}</a>
      <p>${escapeHtml(item.path)}</p>
    </article>`).join('');
  results.classList.remove('hidden');
}

async function runResearch() {
  statusBox.className = 'status';
  statusBox.textContent = '正在请求模型并等待工具调用…';
  statusBox.classList.remove('hidden');
  results.classList.add('hidden');
  button.disabled = true;
  try {
    const response = await fetch('/api/research', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({question: question.value})
    });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || `HTTP ${response.status}`);
    renderResult(data);
    statusBox.textContent = data.mode === 'demo'
      ? '离线链路已完成：未调用 Hy3。'
      : '实时 Hy3 工具调用与报告已完成。';
  } catch (error) {
    statusBox.className = 'status error';
    statusBox.textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

question.addEventListener('input', updateCounter);
button.addEventListener('click', runResearch);
updateCounter();
loadHealth();
