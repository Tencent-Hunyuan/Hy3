/**
 * Hy3 Academic Writing Assistant — Main Script
 *
 * 功能：
 * 1. AI 对话（支持推理模式切换）
 * 2. 论文润色（三种模式：学术润色 / 精简压缩 / 中英互译）
 *
 * API 调用：OpenAI 兼容 Chat Completions（流式）
 */

// ========== State ==========
const state = {
    provider: 'selfhost',
    baseUrl: 'http://127.0.0.1:8000/v1',
    apiKey: 'EMPTY',
    model: 'hy3',
    temperature: 0.9,
    maxTokens: 4096,
    reasoningEffort: 'no_think',
    polishMode: 'academic',
    connectionOK: false,
    chatMessages: [],   // { role, content }
    isStreaming: false,
    abortController: null,
};

// ========== DOM Refs ==========
const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);

// ========== Sidebar ==========
function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('collapsed');
}

function handleProviderChange() {
    const provider = $('#providerSelect').value;
    state.provider = provider;

    switch (provider) {
        case 'selfhost':
            $('#baseUrl').value = 'http://127.0.0.1:8000/v1';
            $('#apiKey').value = 'EMPTY';
            $('#modelName').value = 'hy3';
            break;
        case 'openrouter':
            $('#baseUrl').value = 'https://openrouter.ai/api/v1';
            $('#apiKey').value = '';
            $('#modelName').value = 'tencent/hy3';
            break;
        case 'custom':
            // keep current values
            break;
    }
	syncState();
}

function toggleKeyVisibility() {
    const input = $('#apiKey');
    const btn = $('#toggleKeyBtn');
    if (input.type === 'password') {
        input.type = 'text';
        btn.textContent = '🙈';
    } else {
        input.type = 'password';
        btn.textContent = '👁';
    }
}

function syncState() {
    state.baseUrl     = $('#baseUrl').value.trim();
    state.apiKey      = $('#apiKey').value.trim();
    state.model       = $('#modelName').value.trim();
    state.temperature = parseFloat($('#temperature').value);
    state.maxTokens   = parseInt($('#maxTokens').value);
    $('#modelBadge').textContent = state.model || 'hy3';
}

async function testConnection() {
    syncState();
    const statusEl = $('#connStatus');
    const btn = $('#testConnBtn');
    btn.textContent = '测试中...';
    btn.classList.add('testing');
    statusEl.textContent = '';
    statusEl.className = 'status-text';

    try {
        const res = await fetch(`${state.baseUrl}/chat/completions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${state.apiKey}`,
            },
            body: JSON.stringify({
                model: state.model,
                messages: [{ role: 'user', content: 'Hi' }],
                max_tokens: 5,
                temperature: state.temperature,
                top_p: 1.0,
            }),
            signal: AbortSignal.timeout(15000),
        });

        if (res.ok) {
            state.connectionOK = true;
            statusEl.textContent = '✅ 连接成功';
            statusEl.className = 'status-text success';
        } else {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.error?.message || `HTTP ${res.status}`);
        }
    } catch (e) {
        state.connectionOK = false;
        statusEl.textContent = `❌ ${e.message}`;
        statusEl.className = 'status-text error';
    } finally {
        btn.textContent = '测试连接';
        btn.classList.remove('testing');
    }
}

// ========== Tabs ==========
function switchTab(tabName) {
    $$('.tab').forEach(t => t.classList.remove('active'));
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

    $$('.tab-content').forEach(c => c.classList.remove('active'));
    $(`#${tabName}Tab`).classList.add('active');
}

// ========== Chat ==========
function updateReasoningBadge() {
    state.reasoningEffort = $('#reasoningToggle').checked ? 'high' : 'no_think';
}

function handleChatKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

function quickPrompt(text) {
    $('#chatInput').value = text;
    sendMessage();
}

async function sendMessage() {
    if (state.isStreaming) return;
    syncState();

    const inputEl = $('#chatInput');
    const content = inputEl.value.trim();
    if (!content) return;

    // Remove welcome screen
    const welcome = document.querySelector('.welcome-screen');
    if (welcome) welcome.remove();

    // Add user message
    appendMessage('user', content);
    state.chatMessages.push({ role: 'user', content });

    inputEl.value = '';
    inputEl.style.height = 'auto';
    $('#sendBtn').disabled = true;

    // Add assistant placeholder
    const assistantMsg = appendMessage('assistant', '', true);
    const contentEl = assistantMsg.querySelector('.msg-content');

    // Prepare messages
    const messages = [...state.chatMessages];

    state.isStreaming = true;
    state.abortController = new AbortController();
    $('#chatStatus').textContent = '';

    try {
        const response = await fetch(`${state.baseUrl}/chat/completions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${state.apiKey}`,
            },
            body: JSON.stringify({
                model: state.model,
                messages: messages,
                temperature: state.temperature,
                top_p: 1.0,
                max_tokens: state.maxTokens,
                stream: true,
                extra_body: {
                    chat_template_kwargs: {
                        reasoning_effort: state.reasoningEffort,
                    },
                },
            }),
            signal: state.abortController.signal,
        });

        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.error?.message || `API Error: ${response.status}`);
        }

        // Stream reading
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullContent = '';
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop(); // keep incomplete line

            for (const line of lines) {
                const trimmed = line.trim();
                if (!trimmed || !trimmed.startsWith('data: ')) continue;
                const data = trimmed.slice(6);
                if (data === '[DONE]') continue;

                try {
                    const parsed = JSON.parse(data);
                    const delta = parsed.choices?.[0]?.delta?.content;
                    if (delta) {
                        fullContent += delta;
                        contentEl.textContent = fullContent;
                        // Auto scroll
                        const container = $('#chatMessages');
                        container.scrollTop = container.scrollHeight;
                    }
                } catch {
                    // skip malformed chunks
                }
            }
        }

        contentEl.classList.remove('streaming');
        state.chatMessages.push({ role: 'assistant', content: fullContent });

    } catch (e) {
        if (e.name === 'AbortError') {
            contentEl.textContent = (contentEl.textContent || '') + '\n\n[已中断]';
        } else {
            contentEl.textContent = `❌ 错误: ${e.message}`;
            $('#chatStatus').textContent = `请求失败: ${e.message}`;
            $('#chatStatus').className = 'status-text error';
        }
        contentEl.classList.remove('streaming');
    } finally {
        state.isStreaming = false;
        state.abortController = null;
        $('#sendBtn').disabled = false;
        $('#chatInput').focus();
    }
}

function appendMessage(role, content, streaming = false) {
    const container = $('#chatMessages');
    const div = document.createElement('div');
    div.className = `message ${role}`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'msg-content' + (streaming ? ' streaming' : '');
    if (content) contentDiv.textContent = content;

    div.appendChild(contentDiv);
    container.appendChild(div);

    container.scrollTop = container.scrollHeight;
    return div;
}

function clearChat() {
    state.chatMessages = [];
    $('#chatMessages').innerHTML = `
        <div class="welcome-screen">
            <div class="welcome-icon">
                <svg width="64" height="64" viewBox="0 0 64 64">
                    <circle cx="32" cy="32" r="30" fill="none" stroke="url(#welcomeGrad)" stroke-width="2"/>
                    <text x="32" y="40" text-anchor="middle" fill="#667eea" font-size="28" font-weight="bold">H3</text>
                    <defs>
                        <linearGradient id="welcomeGrad" x1="0" y1="0" x2="64" y2="64">
                            <stop offset="0%" stop-color="#667eea"/>
                            <stop offset="100%" stop-color="#764ba2"/>
                        </linearGradient>
                    </defs>
                </svg>
            </div>
            <h2>Hy3 智能助手</h2>
            <p>由腾讯混元 295B MoE 模型驱动 · 256K 上下文 · 深度推理</p>
            <div class="quick-prompts">
                <span>试试这些：</span>
                <div class="prompt-chips">
                    <button onclick="quickPrompt('用 Python 写一个快速排序算法，附带注释')">🔢 算法实现</button>
                    <button onclick="quickPrompt('解释什么是 Transformer 注意力机制')">🧠 技术概念</button>
                    <button onclick="quickPrompt('帮我写一个 RESTful API 的接口文档模板')">📝 文档模板</button>
                    <button onclick="quickPrompt('对比 vLLM 和 SGLang 的优缺点')">⚡ 框架对比</button>
                </div>
            </div>
        </div>
    `;
}

// ========== Polish ==========
const polishModePrompts = {
    academic: `你是一位专业的学术论文润色专家。请对以下文本进行学术润色：

要求：
1. 提升学术性和正式度，使用更精确的学术术语
2. 优化句式结构，避免口语化表达
3. 确保逻辑连贯，段落过渡自然
4. 修正语法、拼写和标点错误
5. 保持原文的核心意思不变
6. 如果原文是中文，输出润色后的中文；如果是英文，输出英文

请直接输出润色后的文本，不需要解释修改了什么。`,

    concise: `你是一位专业的文本精简专家。请对以下文本进行精简压缩：

要求：
1. 去除冗余表达和重复内容
2. 合并相似观点，提炼核心信息
3. 保留所有关键数据和结论
4. 字数压缩至原文的 60%-70%
5. 确保压缩后的文本仍然逻辑清晰、可独立阅读

请直接输出精简后的文本。`,

    translate: `你是一位专业的学术翻译专家。请对以下文本进行翻译：

要求：
- 如果原文是中文，翻译为英文（学术英语风格）
- 如果原文是英文，翻译为中文（学术中文风格）
- 保持专业术语的准确翻译
- 保留原文的学术风格和语调

请直接输出翻译后的文本。`,
};

function setPolishMode(mode, btn) {
    state.polishMode = mode;
    $$('.mode-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
}

// Char count
$('#polishInput').addEventListener('input', function () {
    $('#inputCharCount').textContent = `${this.value.length} 字`;
});

async function runPolish() {
    if (state.isStreaming) return;
    syncState();

    const input = $('#polishInput').value.trim();
    if (!input) {
        alert('请先在左侧输入需要润色的文本');
        return;
    }

    const btn = $('#polishBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="loading-dots"><span></span><span></span><span></span></span> 润色中...';

    const outputEl = $('#polishOutput');
    outputEl.innerHTML = '';
    $('#polishStatus').textContent = '';
    $('#polishStatus').className = 'status-text';
    $('#outputCharCount').textContent = '0 字';

    const systemPrompt = polishModePrompts[state.polishMode];
    state.isStreaming = true;
    state.abortController = new AbortController();

    try {
        const response = await fetch(`${state.baseUrl}/chat/completions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${state.apiKey}`,
            },
            body: JSON.stringify({
                model: state.model,
                messages: [
                    { role: 'system', content: systemPrompt },
                    { role: 'user', content: input },
                ],
                temperature: 0.7,
                top_p: 1.0,
                max_tokens: Math.max(state.maxTokens, input.length * 2),
                stream: true,
                extra_body: {
                    chat_template_kwargs: {
                        reasoning_effort: 'high', // 润色启用深度推理
                    },
                },
            }),
            signal: state.abortController.signal,
        });

        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.error?.message || `API Error: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullContent = '';
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                const trimmed = line.trim();
                if (!trimmed || !trimmed.startsWith('data: ')) continue;
                const data = trimmed.slice(6);
                if (data === '[DONE]') continue;

                try {
                    const parsed = JSON.parse(data);
                    const delta = parsed.choices?.[0]?.delta?.content;
                    if (delta) {
                        fullContent += delta;
                        outputEl.textContent = fullContent;
                        $('#outputCharCount').textContent = `${fullContent.length} 字`;
                    }
                } catch { /* skip */ }
            }
        }

        $('#polishStatus').textContent = '✅ 润色完成';
        $('#polishStatus').className = 'status-text success';

    } catch (e) {
        if (e.name === 'AbortError') {
            outputEl.textContent = (outputEl.textContent || '') + '\n\n[已中断]';
        } else {
            outputEl.textContent = `❌ 错误: ${e.message}`;
            $('#polishStatus').textContent = `请求失败: ${e.message}`;
            $('#polishStatus').className = 'status-text error';
        }
    } finally {
        state.isStreaming = false;
        state.abortController = null;
        btn.disabled = false;
        btn.innerHTML = `<svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path d="M1 9l4 4 8-8" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg> 开始润色`;
    }
}

function copyPolishResult() {
    const text = $('#polishOutput').textContent.trim();
    if (!text || text.startsWith('❌')) return;
    navigator.clipboard.writeText(text).then(() => {
        const btn = document.querySelector('.output-actions .action-btn');
        const orig = btn.textContent;
        btn.textContent = '✅';
        setTimeout(() => btn.textContent = orig, 1500);
    });
}

function downloadPolishResult() {
    const text = $('#polishOutput').textContent.trim();
    if (!text || text.startsWith('❌')) return;
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `hy3-polished-${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(a.href);
}

// ========== Background Animation ==========
(function initBackground() {
    const canvas = $('#bgCanvas');
    const ctx = canvas.getContext('2d');
    let particles = [];
    let animId;

    function resize() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }
    resize();
    window.addEventListener('resize', resize);

    class Particle {
        constructor() {
            this.reset();
        }
        reset() {
            this.x = Math.random() * canvas.width;
            this.y = Math.random() * canvas.height;
            this.size = Math.random() * 2 + 1;
            this.speedX = (Math.random() - 0.5) * 0.4;
            this.speedY = (Math.random() - 0.5) * 0.4;
            this.opacity = Math.random() * 0.3 + 0.05;
        }
        update() {
            this.x += this.speedX;
            this.y += this.speedY;
            if (this.x < 0 || this.x > canvas.width) this.speedX *= -1;
            if (this.y < 0 || this.y > canvas.height) this.speedY *= -1;
        }
        draw() {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(102,126,234,${this.opacity})`;
            ctx.fill();
        }
    }

    function initParticles(count = 60) {
        particles = Array.from({ length: count }, () => new Particle());
    }

    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Draw connections
        for (let i = 0; i < particles.length; i++) {
            for (let j = i + 1; j < particles.length; j++) {
                const dx = particles[i].x - particles[j].x;
                const dy = particles[i].y - particles[j].y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < 120) {
                    ctx.beginPath();
                    ctx.moveTo(particles[i].x, particles[i].y);
                    ctx.lineTo(particles[j].x, particles[j].y);
                    ctx.strokeStyle = `rgba(102,126,234,${0.06 * (1 - dist / 120)})`;
                    ctx.stroke();
                }
            }
        }

        particles.forEach(p => {
            p.update();
            p.draw();
        });

        animId = requestAnimationFrame(animate);
    }

    initParticles();
    animate();
})();

// ========== Auto-resize textarea ==========
$('#chatInput').addEventListener('input', function () {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 120) + 'px';
});

// ========== Init ==========
syncState();
