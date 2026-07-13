#!/usr/bin/env node
/**
 * Demo: 流式对话（直连 Hy3 API，支持 Mock 模式）
 * 用法: node demos/chat-demo.js "你的问题"
 *       node demos/chat-demo.js --think "复杂问题"
 *       HY3_MOCK=1 node demos/chat-demo.js       (Mock 模式)
 */

const https = require('https');
const fs = require('fs');
const path = require('path');

function loadEnv() {
  const envPath = path.join(__dirname, '..', '.env');
  if (!fs.existsSync(envPath)) return;
  const text = fs.readFileSync(envPath, 'utf-8');
  for (const line of text.split('\n')) {
    const m = line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$/);
    if (!m) continue;
    let val = m[2];
    if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'")))
      val = val.slice(1, -1);
    if (process.env[m[1]] === undefined) process.env[m[1]] = val;
  }
}
loadEnv();

const API_KEY = process.env.HY3_API_KEY;
const BASE_URL = process.env.HY3_BASE_URL || 'https://tokenhub.tencentmaas.com/v1';
const MODEL = process.env.HY3_MODEL || 'hy3';
const MOCK = process.env.HY3_MOCK === '1' || !API_KEY;

const args = process.argv.slice(2);
let think = false;
let question;

if (args[0] === '--think') {
  think = true;
  question = args.slice(1).join(' ') || '你好，请介绍一下你自己';
} else {
  question = args.join(' ') || '你好，请介绍一下你自己';
}

if (MOCK) {
  // ===== Mock 模式：本地模拟流式回复 =====
  console.log('[' + MODEL + ' Mock' + (think ? ' 深度思考' : '') + ']\n');
  console.log('> ' + question + '\n');

  if (think) {
    const reasoning = `分析用户问题"${question}"。这是一个简单/中等复杂度的查询，我需要给出清晰有帮助的回答。`;
    process.stderr.write('\x1b[90m' + reasoning + '\x1b[0m\n');
  }

  const mockReply = `你好！这是 Mock 模式下 ${MODEL} 对「${question}」的模拟回复。

未连接真实 API，启动 Mock 模式即可预览界面效果。配置 HY3_API_KEY 后自动切换为真实调用。`;

  const chunks = mockReply.split(/(?<=\S{2})|(?<=\s)/).filter(Boolean);
  (async () => {
    for (const c of chunks) {
      process.stdout.write(c);
      await new Promise(r => setTimeout(r, 40 + Math.random() * 60));
    }
    console.log();
  })();
  return;
}

// ===== 真实 API 模式 =====
console.log(`> ${question}${think ? '  [深度思考已开启]' : ''}\n`);

const url = new URL('/v1/chat/completions', BASE_URL);
const payload = JSON.stringify({
  model: MODEL,
  messages: [{ role: 'user', content: question }],
  stream: true,
  ...(think ? { reasoning_effort: 'high', thinking: { type: 'enabled' } } : {})
});

const req = https.request(
  url.href,
  {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${API_KEY}`
    }
  },
  (res) => {
    if (res.statusCode !== 200) {
      let body = '';
      res.on('data', c => body += c);
      res.on('end', () => { console.error(`API ${res.statusCode}: ${body.slice(0, 300)}`); process.exit(1); });
      return;
    }

    let buf = '';
    res.on('data', (chunk) => {
      buf += chunk.toString();
      const lines = buf.split('\n');
      buf = lines.pop() || '';
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const data = line.slice(6);
        if (data === '[DONE]') { process.stdout.write('\n'); continue; }
        try {
          const json = JSON.parse(data);
          const delta = json.choices?.[0]?.delta;
          if (!delta) continue;
          if (delta.reasoning_content) process.stderr.write('\x1b[90m' + delta.reasoning_content + '\x1b[0m');
          if (delta.content) process.stdout.write(delta.content);
        } catch {}
      }
    });
    res.on('end', () => process.exit(0));
    res.on('error', (err) => { console.error('\n' + err.message); process.exit(1); });
  }
);

req.on('error', (err) => { console.error('请求失败:', err.message); process.exit(1); });
req.write(payload);
req.end();
