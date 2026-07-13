#!/usr/bin/env node
/**
 * Demo: 翻译重写（直连 Hy3 API，支持 Mock 模式）
 * 用法: node demos/translate-demo.js
 *       node demos/translate-demo.js "要翻译的文本" zh2en casual
 *       HY3_MOCK=1 node demos/translate-demo.js
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

const LANG_MAP = {
  zh2en: { name: '英文', prompt: '将以下中文翻译为自然流畅的英文' },
  en2zh: { name: '中文', prompt: '将以下英文翻译为自然流畅的中文' },
  zh2ja: { name: '日文', prompt: '将以下中文翻译为自然流畅的日文' },
  zh2ko: { name: '韩文', prompt: '将以下中文翻译为自然流畅的韩文' },
  zh2fr: { name: '法文', prompt: '将以下中文翻译为自然流畅的法文' },
  zh2de: { name: '德文', prompt: '将以下中文翻译为自然流畅的德文' },
  zh2es: { name: '西班牙文', prompt: '将以下中文翻译为自然流畅的西班牙文' },
  zh2ru: { name: '俄文', prompt: '将以下中文翻译为自然流畅的俄文' },
  zh2ar: { name: '阿拉伯文', prompt: '将以下中文翻译为自然流畅的阿拉伯文' },
  en2ja: { name: '日文', prompt: '将以下英文翻译为自然流畅的日文' },
  en2ko: { name: '韩文', prompt: '将以下英文翻译为自然流畅的韩文' },
  en2fr: { name: '法文', prompt: '将以下英文翻译为自然流畅的法文' },
  en2de: { name: '德文', prompt: '将以下英文翻译为自然流畅的德文' },
  en2es: { name: '西班牙文', prompt: '将以下英文翻译为自然流畅的西班牙文' },
  auto:  { name: '自动检测', prompt: '检测以下文本语言，翻译为另一种语言（中→英 / 英→中）' }
};

const STYLE_MAP = {
  casual:    '使用日常口语化表达，自然随意',
  formal:    '使用正式书面语，严谨规范',
  academic:  '使用学术论文风格，精准专业',
  technical: '使用技术文档风格，术语准确',
  marketing: '使用营销文案风格，引人入胜',
  creative:  '使用创意文学风格，富有文采',
  social:    '使用社交媒体风格，生动有趣'
};

const MOCK_TRANSLATIONS = {
  zh2en: { zh: '人工智能正在改变世界', en: 'Artificial intelligence is changing the world' },
  en2zh: { en: 'The future is now', zh: '未来已来' },
  default: { out: '[Mock] 翻译结果 — 配置 API Key 后获取真实翻译' }
};

function doMock(text, direction, style) {
  const pair = MOCK_TRANSLATIONS[direction];
  let result;
  if (pair) {
    result = direction.startsWith('zh') ? (pair.en + ` [${style}]`)
           : direction.startsWith('en') ? (pair.zh + ` [${style}]`)
           : `[Mock] (${LANG_MAP[direction]?.name || direction}) ${text} [${style}]`;
  } else {
    result = `[Mock] (${LANG_MAP[direction]?.name || direction}) ${text} [${style}]`;
  }
  return result;
}

function realTranslate(text, direction, style) {
  return new Promise((resolve, reject) => {
    const lang = LANG_MAP[direction] || LANG_MAP.auto;
    const styleGuide = STYLE_MAP[style] || STYLE_MAP.casual;
    const prompt = direction === 'auto'
      ? `${lang.prompt}。\n\n文本：${text}`
      : `${lang.prompt}。\n风格要求：${styleGuide}。\n\n原文：${text}`;

    const url = new URL('/v1/chat/completions', BASE_URL);
    const body = JSON.stringify({
      model: MODEL,
      messages: [
        { role: 'system', content: '你是一名专业的多语种翻译专家。输出仅包含译文，不要添加解释、注释或额外对话。' },
        { role: 'user', content: prompt }
      ],
      stream: false,
      temperature: 0.2
    });

    const req = https.request(
      url.href,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${API_KEY}` }
      },
      (res) => {
        let data = '';
        res.on('data', c => data += c);
        res.on('end', () => {
          try {
            const json = JSON.parse(data);
            resolve((json.choices?.[0]?.message?.content || '').trim());
          } catch (e) { reject(e); }
        });
      }
    );
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

const args = process.argv.slice(2);
const customText = args[0];
const customDir = args[1] || 'zh2en';
const customStyle = args[2] || 'casual';

if (customText) {
  // 单次翻译
  (async () => {
    console.log('[' + MODEL + (MOCK ? ' Mock' : '') + ']');
    console.log(`[${LANG_MAP[customDir]?.name || customDir}] ${customStyle}`);
    console.log(`原文: ${customText}`);
    if (MOCK) {
      console.log(`译文: ${doMock(customText, customDir, customStyle)}`);
    } else {
      console.log('翻译中...');
      try {
        const result = await realTranslate(customText, customDir, customStyle);
        console.log(`译文: ${result}`);
      } catch (err) {
        console.error('请求失败:', err.message);
        process.exit(1);
      }
    }
  })();
} else {
  // 批量测试
  const testCases = [
    { text: '人工智能正在深刻改变各行各业的工作方式，从医疗诊断到金融风控，从智能客服到自动驾驶，AI 的触角无处不在。', direction: 'zh2en', label: '中文 → 英文' },
    { text: 'The emergence of large language models has fundamentally reshaped how we approach natural language processing tasks.', direction: 'en2zh', label: '英文 → 中文' },
  ];

  (async () => {
    console.log('翻译重写 Demo' + (MOCK ? ' [Mock]' : ''));
    console.log('='.repeat(50));

    for (const tc of testCases) {
      console.log(`\n[${tc.label}]`);
      console.log(`原文: ${tc.text}`);
      if (MOCK) {
        console.log(`译文: ${doMock(tc.text, tc.direction, 'casual')}`);
      } else {
        try {
          const result = await realTranslate(tc.text, tc.direction, 'casual');
          console.log(`译文: ${result}`);
        } catch (err) {
          console.error('请求失败:', err.message);
        }
      }
    }

    console.log('\n' + '='.repeat(50));
    console.log('翻译演示完毕');
  })().catch((err) => { console.error('请求失败:', err.message); process.exit(1); });
}
