// src/hy3-client.js
// Hy3 核心客户端：环境配置、HTTP 工具、SSE 代理、Express 基础路由

const fs = require('fs');
const path = require('path');
const http = require('http');
const https = require('https');
const express = require('express');

// ==================== 手动加载 .env（无需 dotenv 依赖） ====================
function loadEnv() {
  const envPath = path.join(__dirname, '..', '.env');
  if (!fs.existsSync(envPath)) return;
  const text = fs.readFileSync(envPath, 'utf-8');
  for (const line of text.split('\n')) {
    const m = line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$/);
    if (!m) continue;
    let val = m[2];
    if (val.startsWith('"') && val.endsWith('"')) val = val.slice(1, -1).replace(/\\"/g, '"');
    else if (val.startsWith("'") && val.endsWith("'")) val = val.slice(1, -1);
    if (process.env[m[1]] === undefined) process.env[m[1]] = val;
  }
}
loadEnv();

const PORT = process.env.PORT || 3000;
const API_KEY = process.env.HY3_API_KEY;
const BASE_URL = process.env.HY3_BASE_URL || 'https://tokenhub.tencentmaas.com/v1';
const MODEL = process.env.HY3_MODEL || 'hy3';
const MOCK = process.env.HY3_MOCK === '1';

// ==================== 日志 ====================
function log(...args) {
  const t = new Date().toISOString().replace('T', ' ').slice(0, 19);
  console.log(`[${t}]`, ...args);
}

// ==================== HTTP/HTTPS 请求 ====================
function requestHttp(url, options, callback) {
  const mod = url.startsWith('https') ? https : http;
  return mod.request(url, options, callback);
}

// ==================== 公共：SSE 代理（支持推理/思考内容） ====================
function proxySSE(res, reqBody, { mockContent } = {}) {
  if (MOCK) {
    (async () => {
      const chunks = mockContent
        ? mockContent.split(/(?<=\S{3})|(?<=\s)/).filter(Boolean)
        : ['Mock 模式\n', '未调用真实 API。'];
      for (const c of chunks) {
        res.write(`data: ${JSON.stringify({ type: 'text', content: c })}\n\n`);
        await new Promise(r => setTimeout(r, 80 + Math.random() * 120));
      }
      res.write(`data: ${JSON.stringify({ type: 'done' })}\n\n`);
      res.end();
    })();
    return;
  }

  const body = JSON.stringify({ model: MODEL, stream: true, ...reqBody });

  const proxyReq = requestHttp(
    `${BASE_URL}/chat/completions`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${API_KEY}`
      }
    },
    (proxyRes) => {
      let buf = '';
      proxyRes.on('data', (chunk) => {
        buf += chunk.toString();
        const lines = buf.split('\n');
        buf = lines.pop() || '';
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const payload = line.slice(6);
          if (payload === '[DONE]') {
            res.write(`data: ${JSON.stringify({ type: 'done' })}\n\n`);
            continue;
          }
          try {
            const json = JSON.parse(payload);
            const delta = json.choices?.[0]?.delta;
            if (!delta) continue;

            // 思考 / 推理内容
            const reasoning = delta.reasoning_content
              || delta.reasoning
              || delta.thinking
              || delta.thought;
            if (reasoning) {
              res.write(`data: ${JSON.stringify({ type: 'reasoning', text: reasoning })}\n\n`);
            }

            // 正文内容
            if (delta.content) {
              res.write(`data: ${JSON.stringify({ type: 'text', content: delta.content })}\n\n`);
            }
          } catch (e) { /* 跳过无法解析的行 */ }
        }
      });
      proxyRes.on('end', () => {
        res.write(`data: ${JSON.stringify({ type: 'done' })}\n\n`);
        res.end();
      });
      proxyRes.on('error', (err) => {
        res.write(`data: ${JSON.stringify({ type: 'error', message: err.message })}\n\n`);
        res.end();
      });
    }
  );
  proxyReq.on('error', (err) => {
    res.write(`data: ${JSON.stringify({ type: 'error', message: err.message })}\n\n`);
    res.end();
  });
  proxyReq.write(body);
  proxyReq.end();
}

// ==================== 创建 Express 应用 ====================
function createApp() {
  const app = express();
  app.use(express.json());
  app.use(express.static('public'));

  // 启动提示
  if (!API_KEY && !MOCK) {
    log('Warning: HY3_API_KEY not configured.');
    log('Server will return 500 errors for API requests until configured.');
  } else if (MOCK) {
    log('Mock mode enabled. Running without real API.');
  } else {
    log('API configured. Backend: ' + BASE_URL + ', model: ' + MODEL);
  }
  log('Server starting on http://localhost:' + PORT);

  // ==================== 健康检查 ====================
  app.get('/api/health', (req, res) => {
    res.json({
      ok: !!(API_KEY || MOCK),
      model: MODEL,
      mock: MOCK,
      apiConfigured: !!API_KEY
    });
  });

  // ==================== 智能对话（支持深度思考） ====================
  app.post('/api/chat', async (req, res) => {
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');

    if (!API_KEY && !MOCK) {
      res.write(`data: ${JSON.stringify({ type: 'error', message: 'API Key 未配置' })}\n\n`);
      res.end();
      return;
    }

    const { messages, think = false } = req.body;

    const payload = {
      messages: messages || [],
      ...(think ? { reasoning_effort: 'high', thinking: { type: 'enabled' } } : {})
    };

    proxySSE(res, payload);
  });

  return app;
}

module.exports = {
  createApp,
  proxySSE,
  requestHttp,
  log,
  loadEnv,
  PORT,
  API_KEY,
  BASE_URL,
  MODEL,
  MOCK
};
