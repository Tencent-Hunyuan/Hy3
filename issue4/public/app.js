// public/app.js
// Hy3 助手前端逻辑：SSE 流式渲染、Tab 切换、API 调用

// ==================== 工具函数 ====================
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

function Escape(s) {
  if (!s) return '';
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

async function api(path, opts = {}) {
  const { method = 'GET', body } = opts;
  const init = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) init.body = JSON.stringify(body);
  const res = await fetch(path, init);
  if (!res.ok) {
    const err = await res.text().catch(() => 'Unknown error');
    throw new Error(`HTTP ${res.status}: ${err}`);
  }
  return res;
}

// ==================== 状态检查 ====================
async function checkHealth() {
  try {
    const res = await fetch('/api/health');
    const data = await res.json();
    const badge = $('#status');
    if (data.ok) {
      badge.textContent = '\u2713 ' + data.model + ' 已就绪';
      badge.className = 'status-badge ok';
    } else {
      badge.textContent = '\u26A0 API Key 未配置';
      badge.className = 'status-badge err';
    }
  } catch {
    $('#status').textContent = '\u2717 服务未连接';
    $('#status').className = 'status-badge err';
  }
}
checkHealth();

// ==================== Tab 切换 ====================
$$('.tab').forEach((tab) => {
  tab.addEventListener('click', () => {
    $$('.tab').forEach((t) => t.classList.remove('active'));
    $$('.panel').forEach((p) => p.classList.remove('active'));
    tab.classList.add('active');
    $(`#panel-${tab.dataset.tab}`).classList.add('active');
  });
});

// ==================== SSE 辅助 ====================
async function* readSSE(response) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buf = '';
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const lines = buf.split('\n');
    buf = lines.pop() || '';
    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed.startsWith('data: ')) {
        try {
          yield JSON.parse(trimmed.slice(6));
        } catch {}
      }
    }
  }
}

// ==================== 对话面板 ====================
const chatBox = $('#chatBox');
const chatInput = $('#chatInput');
const chatSend = $('#chatSend');
const thinkToggle = $('#thinkToggle');

function addMsg(role, text, cls) {
  const div = document.createElement('div');
  div.className = `msg ${role}` + (cls ? ' ' + cls : '');
  div.textContent = text;
  chatBox.appendChild(div);
  chatBox.scrollTop = chatBox.scrollHeight;
  return div;
}

async function sendChat() {
  const msg = chatInput.value.trim();
  if (!msg) return;
  addMsg('user', msg);
  chatInput.value = '';
  chatSend.disabled = true;

  let assistantDiv = null;
  let thinkingDiv = null;

  try {
    const res = await api('/api/chat', {
      method: 'POST',
      body: { messages: [{ role: 'user', content: msg }], think: thinkToggle.checked },
    });

    for await (const evt of readSSE(res)) {
      switch (evt.type) {
        case 'reasoning':
          if (!thinkingDiv) {
            thinkingDiv = addMsg('assistant', '', 'thinking');
            const toggle = document.createElement('button');
            toggle.className = 'thinking-toggle';
            toggle.textContent = '思考过程';
            thinkingDiv.appendChild(toggle);
            thinkingDiv._content = document.createElement('div');
            thinkingDiv._content.className = 'thinking-content';
            thinkingDiv.appendChild(thinkingDiv._content);
            toggle.addEventListener('click', () => {
              const c = thinkingDiv._content;
              c.style.display = c.style.display === 'none' ? 'block' : 'none';
            });
          }
          if (!assistantDiv) {
            assistantDiv = document.createElement('div');
            assistantDiv.className = 'msg assistant';
            chatBox.appendChild(assistantDiv);
          }
          thinkingDiv._content.textContent += evt.text;
          chatBox.scrollTop = chatBox.scrollHeight;
          break;
        case 'text':
          if (!assistantDiv) {
            assistantDiv = document.createElement('div');
            assistantDiv.className = 'msg assistant';
            chatBox.appendChild(assistantDiv);
          }
          assistantDiv.textContent += evt.content;
          chatBox.scrollTop = chatBox.scrollHeight;
          break;
        case 'done':
          break;
        case 'error':
          addMsg('assistant', '错误：' + evt.message);
          break;
      }
    }
  } catch (e) {
    addMsg('assistant', '请求失败：' + e.message);
  }
  chatSend.disabled = false;
}

chatSend.addEventListener('click', sendChat);
chatInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat(); }
});

// ==================== 研究面板 ====================
const researchTopic = $('#researchTopic');
const researchStart = $('#researchStart');
const researchOutput = $('#researchOutput');
const researchThinkToggle = $('#researchThinkToggle');

async function startResearch() {
  const topic = researchTopic.value.trim();
  if (!topic) return;
  researchOutput.innerHTML = '<p class="hint">正在分析主题，Hy3 将生成深度研究报告...</p>';
  researchStart.disabled = true;

  try {
    const res = await api('/api/research', {
      method: 'POST',
      body: { topic, think: researchThinkToggle.checked },
    });

    let html = '';
    let thinkingHtml = '';
    let hasThinking = false;
    let hasContent = false;

    for await (const evt of readSSE(res)) {
      switch (evt.type) {
        case 'reasoning':
          thinkingHtml += Escape(evt.text);
          if (!hasThinking) hasThinking = true;
          break;
        case 'text':
          if (!hasContent) {
            html = '';
            hasContent = true;
          }
          html += Escape(evt.content);
          break;
        case 'done':
          break;
        case 'error':
          html += '<p style="color:var(--err)">错误：' + Escape(evt.message) + '</p>';
          break;
      }
      renderResearch(html, thinkingHtml, hasThinking);
      researchOutput.scrollTop = researchOutput.scrollHeight;
    }

    if (!hasContent && hasThinking) {
      researchOutput.innerHTML = '<p class="hint">模型只返回了推理过程，未生成正文内容。请尝试关闭深度思考再试。</p>';
    }
  } catch (e) {
    researchOutput.innerHTML = '<p style="color:var(--err)">请求失败：' + Escape(e.message) + '</p>';
  }
  researchStart.disabled = false;
}

function renderResearch(contentHtml, thinkingHtml, hasThinking) {
  if (hasThinking) {
    researchOutput.innerHTML =
      '<details class="thinking-box" open>' +
      '<summary>推理过程</summary>' +
      '<div class="thinking-content">' + thinkingHtml + '</div>' +
      '</details>' +
      '<div class="research-body">' + contentHtml + '</div>';
  } else {
    researchOutput.innerHTML = contentHtml;
  }
}

researchStart.addEventListener('click', startResearch);
researchTopic.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') startResearch();
});

// ==================== 翻译面板 ====================
const sourceText = $('#sourceText');
const translateBtn = $('#translateBtn');
const translateOutput = $('#translateOutput');
const targetLang = $('#targetLang');
const translateStyle = $('#translateStyle');

async function doTranslate() {
  const text = sourceText.value.trim();
  if (!text) return;
  translateOutput.innerHTML = '<p class="hint">正在翻译...</p>';
  translateBtn.disabled = true;

  try {
    const res = await api('/api/translate', {
      method: 'POST',
      body: { text, direction: targetLang.value, style: translateStyle.value },
    });
    const data = await res.json();
    if (data.error) {
      translateOutput.innerHTML = '<p style="color:var(--err)">错误：' + Escape(data.error) + '</p>';
    } else {
      translateOutput.innerHTML = Escape(data.result);
    }
  } catch (e) {
    translateOutput.innerHTML = '<p style="color:var(--err)">请求失败：' + Escape(e.message) + '</p>';
  }
  translateBtn.disabled = false;
}

translateBtn.addEventListener('click', doTranslate);
