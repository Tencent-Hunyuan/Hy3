// src/translator.js
// 翻译重写模块：多语言翻译 + 多风格重写

const { requestHttp, API_KEY, BASE_URL, MODEL, MOCK } = require('./hy3-client');

// ==================== 语言方向映射 ====================
const LANG_MAP = {
  zh2en:  { name: '英文',        prompt: '将以下中文翻译为自然流畅的英文' },
  en2zh:  { name: '中文',        prompt: '将以下英文翻译为自然流畅的中文' },
  zh2ja:  { name: '日文',        prompt: '将以下中文翻译为自然流畅的日文' },
  zh2ko:  { name: '韩文',        prompt: '将以下中文翻译为自然流畅的韩文' },
  zh2fr:  { name: '法文',        prompt: '将以下中文翻译为自然流畅的法文' },
  zh2de:  { name: '德文',        prompt: '将以下中文翻译为自然流畅的德文' },
  zh2es:  { name: '西班牙文',    prompt: '将以下中文翻译为自然流畅的西班牙文' },
  zh2ru:  { name: '俄文',        prompt: '将以下中文翻译为自然流畅的俄文' },
  zh2ar:  { name: '阿拉伯文',    prompt: '将以下中文翻译为自然流畅的阿拉伯文' },
  en2ja:  { name: '日文',        prompt: '将以下英文翻译为自然流畅的日文' },
  en2ko:  { name: '韩文',        prompt: '将以下英文翻译为自然流畅的韩文' },
  en2fr:  { name: '法文',        prompt: '将以下英文翻译为自然流畅的法文' },
  en2de:  { name: '德文',        prompt: '将以下英文翻译为自然流畅的德文' },
  en2es:  { name: '西班牙文',    prompt: '将以下英文翻译为自然流畅的西班牙文' },
  auto:   { name: '自动检测',    prompt: '检测以下文本语言，翻译为另一种语言（中→英 / 英→中）' }
};

// ==================== 风格映射 ====================
const STYLE_MAP = {
  casual:    '使用日常口语化表达，自然随意',
  formal:    '使用正式书面语，严谨规范',
  academic:  '使用学术论文风格，精准专业',
  technical: '使用技术文档风格，术语准确',
  marketing: '使用营销文案风格，引人入胜',
  creative:  '使用创意文学风格，富有文采',
  social:    '使用社交媒体风格，生动有趣'
};

function setupTranslate(app) {
  // ==================== 翻译重写（多国语言 + 风格 + 推理） ====================
  app.post('/api/translate', async (req, res) => {
    if (!API_KEY && !MOCK) {
      return res.status(500).json({ error: 'API Key 未配置' });
    }

    const { text, direction = 'auto', style = 'casual' } = req.body;

    if (MOCK) {
      return res.json({
        result: `[Mock] ${text}`,
        direction,
        style,
        notes: `Mock 模式 — 方向: ${LANG_MAP[direction]?.name || direction}, 风格: ${style}`
      });
    }

    try {
      const lang = LANG_MAP[direction] || LANG_MAP.auto;
      const styleGuide = STYLE_MAP[style] || STYLE_MAP.casual;

      const prompt = direction === 'auto'
        ? `${lang.prompt}。\n\n文本：${text}`
        : `${lang.prompt}。\n风格要求：${styleGuide}。\n\n原文：${text}`;

      const proxyRes = await new Promise((resolve, reject) => {
        const proxyReq = requestHttp(
          `${BASE_URL}/chat/completions`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${API_KEY}`
            }
          },
          (r) => {
            let data = '';
            r.on('data', chunk => data += chunk);
            r.on('end', () => resolve(data));
            r.on('error', reject);
          }
        );
        proxyReq.on('error', reject);
        proxyReq.write(JSON.stringify({
          model: MODEL,
          messages: [
            { role: 'system', content: `你是一名专业的多语种翻译专家。输出仅包含译文，不要添加解释、注释或额外对话。` },
            { role: 'user', content: prompt }
          ],
          stream: false,
          temperature: 0.2
        }));
        proxyReq.end();
      });

      const json = JSON.parse(proxyRes);
      const result = json.choices?.[0]?.message?.content || '';
      res.json({ result, direction, style });
    } catch (e) {
      res.status(500).json({ error: e.message });
    }
  });
}

module.exports = { setupTranslate, LANG_MAP, STYLE_MAP };
