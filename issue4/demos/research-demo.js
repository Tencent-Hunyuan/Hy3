#!/usr/bin/env node
/**
 * Demo: 深度研究（直连 Hy3 API，支持 Mock 模式）
 * 用法: node demos/research-demo.js "研究主题"
 *       node demos/research-demo.js --think "复杂主题"
 *       HY3_MOCK=1 node demos/research-demo.js
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
let topic;

if (args[0] === '--think') {
  think = true;
  topic = args.slice(1).join(' ') || 'AI 对软件工程行业的影响';
} else {
  topic = args.join(' ') || 'AI 对软件工程行业的影响';
}

if (MOCK) {
  // ===== Mock 模式 =====
  console.log('[' + MODEL + ' Mock 研究' + (think ? ' 深度思考' : '') + ']');
  console.log('主题: ' + topic);
  console.log('='.repeat(50));
  console.log();

  if (think) {
    console.log('─'.repeat(40));
    console.log('[推理过程]');
    console.log('─'.repeat(40));
    const reasoning = `分析主题"${topic}"。这涉及多个层面的讨论，包括技术、产业和社会影响。需要从概述、现状、深度剖析、案例、趋势和结论六个维度展开。`;
    process.stderr.write('\x1b[90m' + reasoning + '\x1b[0m\n\n');
    console.log('─'.repeat(40));
    console.log('[研究报告]');
    console.log('─'.repeat(40));
  }

  const mockReport = `## Mock 研究报告：${topic}

### 1. 概述
本报告对「${topic}」进行系统性研究分析。Mock 模式下生成示例内容。

### 2. 现状分析
当前该领域发展迅速，相关技术迭代加快，应用场景持续扩展。

### 3. 深度剖析
- **维度一**：技术创新是核心驱动力
- **维度二**：产业生态正在重塑格局  
- **维度三**：人才需求结构发生变化

### 4. 案例与对比
国内外多个典型案例展示了不同路径的实践效果，各有优劣。

### 5. 趋势展望
未来 3-5 年预计将迎来新一轮突破，值得持续关注。

### 6. 结论
建议保持跟踪、适时布局，抓住关键窗口期。
`;

  const chunks = mockReport.split(/(?<=\S{2})|(?<=\s)/).filter(Boolean);
  (async () => {
    for (const c of chunks) {
      process.stdout.write(c);
      await new Promise(r => setTimeout(r, 30 + Math.random() * 50));
    }
    console.log();
    console.log('='.repeat(50));
    console.log('研究报告生成完毕');
  })();
  return;
}

// ===== 真实 API =====
console.log(`主题: ${topic}${think ? '  [深度思考已开启]' : ''}`);
console.log('='.repeat(50));
console.log();

const systemPrompt = `你是一名深度研究分析师。对用户提供的主题进行全面、深入、结构化的研究。

报告需包含以下结构：
1. **概述** — 主题背景与核心问题
2. **现状分析** — 当前发展和关键数据
3. **深度剖析** — 2-3 个关键维度的深入讨论
4. **案例 / 对比** — 相关案例或多角度对比
5. **趋势展望** — 未来走向与潜在影响
6. **结论与建议** — 总结并给出可操作建议

使用 Markdown 格式。`;

const url = new URL('/v1/chat/completions', BASE_URL);
const payload = JSON.stringify({
  model: MODEL,
  messages: [
    { role: 'system', content: systemPrompt },
    { role: 'user', content: `请对「${topic}」进行深度研究并生成完整报告。` }
  ],
  stream: true,
  ...(think ? { reasoning_effort: 'high', thinking: { type: 'enabled' }, temperature: 0.3 } : { temperature: 0.5 })
});

const req = https.request(
  url.href,
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${API_KEY}` }
  },
  (res) => {
    if (res.statusCode !== 200) {
      let body = '';
      res.on('data', c => body += c);
      res.on('end', () => { console.error(`API ${res.statusCode}: ${body.slice(0, 300)}`); process.exit(1); });
      return;
    }
    let buf = '', hasReasoning = false;
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
          if (delta.reasoning_content) {
            if (!hasReasoning) { console.log('─'.repeat(40)); console.log('[推理过程]'); console.log('─'.repeat(40)); hasReasoning = true; }
            process.stderr.write('\x1b[90m' + delta.reasoning_content + '\x1b[0m');
          }
          if (delta.content) {
            if (hasReasoning) { console.log(); console.log('─'.repeat(40)); console.log('[研究报告]'); console.log('─'.repeat(40)); hasReasoning = false; }
            process.stdout.write(delta.content);
          }
        } catch {}
      }
    });
    res.on('end', () => { console.log(); console.log('='.repeat(50)); console.log('研究报告生成完毕'); process.exit(0); });
    res.on('error', (err) => { console.error('\n' + err.message); process.exit(1); });
  }
);
req.on('error', (err) => { console.error('请求失败:', err.message); process.exit(1); });
req.write(payload);
req.end();
