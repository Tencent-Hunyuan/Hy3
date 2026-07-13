// src/research.js
// 深度研究模块：结构化研究报告生成

const { proxySSE, API_KEY, MOCK } = require('./hy3-client');

const RESEARCH_SYSTEM_PROMPT = `你是一名深度研究分析师。对用户提供的主题进行全面、深入、结构化的研究。

报告需包含以下结构：
1. **概述** — 主题背景与核心问题
2. **现状分析** — 当前发展和关键数据
3. **深度剖析** — 2-3 个关键维度的深入讨论
4. **案例 / 对比** — 相关案例或多角度对比
5. **趋势展望** — 未来走向与潜在影响
6. **结论与建议** — 总结并给出可操作建议

使用 Markdown 格式，数据引用需标注来源。`;

function setupResearch(app) {
  // ==================== 深度研究（深度思考 + 结构化报告） ====================
  app.post('/api/research', async (req, res) => {
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');

    if (!API_KEY && !MOCK) {
      res.write(`data: ${JSON.stringify({ type: 'error', message: 'API Key 未配置' })}\n\n`);
      res.end();
      return;
    }

    const { topic, think = false } = req.body;

    const userMsg = think
      ? `请对「${topic}」进行深度思考研究。请先展示你的推理过程，再给出最终报告。`
      : `请对「${topic}」进行深度研究并生成完整报告。`;

    const payload = {
      messages: [
        { role: 'system', content: RESEARCH_SYSTEM_PROMPT },
        { role: 'user', content: userMsg }
      ],
      ...(think ? { reasoning_effort: 'high', thinking: { type: 'enabled' }, temperature: 0.3 } : { temperature: 0.5 })
    };

    proxySSE(res, payload, {
      mockContent: `## 模拟研究：${topic}\n\n### 概述\n本报告对主题进行了系统性分析。Mock 模式下返回示例内容。\n\n### 现状分析\n当前该领域正处于快速发展阶段。\n\n### 深度剖析\n关键维度一：技术演进路径正从 A 向 B 转变。\n关键维度二：应用场景持续扩展，渗透率逐年提升。\n\n### 趋势展望\n未来 3-5 年将迎来规模化落地窗口期。\n\n### 结论\n建议持续关注并适时布局。`
    });
  });
}

module.exports = { setupResearch, RESEARCH_SYSTEM_PROMPT };
