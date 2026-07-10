import { z } from "zod";
import { extname } from "path";
import { Hy3Client } from "../client.js";
import { renderWordcloudSvg } from "../viz/wordcloud.js";
import { svgToPng } from "../viz/png.js";
import { getTheme } from "../viz/themes.js";
import {
  askHy3,
  buildThemeOverrides,
  loadDataTable,
  resolveLanguage,
  sampleText,
  writeOutputFile,
} from "../utils.js";
import type { ProgressReporter } from "./index.js";

export const wordcloudDefinition = {
  name: "hy3_wordcloud",
  description:
    "Generate a word cloud SVG (or HTML wrapper) from a text, CSV, JSON or XLSX file. Hy3 extracts the top keywords and weights.",
  inputSchema: {
    type: "object" as const,
    properties: {
      file_path: {
        type: "string",
        description: "Path to a text, CSV, JSON or XLSX file.",
      },
      column: {
        type: "string",
        description:
          "For CSV/JSON/XLSX, the text column to analyze. Leave empty to let Hy3 choose.",
      },
      max_words: {
        type: "number",
        description: "Maximum number of words in the cloud.",
        default: 60,
      },
      output_format: {
        type: "string",
        enum: ["svg", "html", "png"],
        description: "'svg' = static SVG; 'html' = HTML page wrapping the SVG; 'png' = PNG image.",
        default: "svg",
      },
      width: {
        type: "number",
        description: "Width in pixels.",
        default: 800,
      },
      height: {
        type: "number",
        description: "Height in pixels.",
        default: 500,
      },
      theme: {
        type: "string",
        enum: [
          "light",
          "dark",
          "colorful",
          "minimal",
          "professional",
          "retro",
          "science",
          "nature",
        ],
        description: "Color theme of the word cloud.",
        default: "light",
      },
      font_family: {
        type: "string",
        description:
          "Custom font family for words and title. Leave empty to use the theme default.",
      },
      background_color: {
        type: "string",
        description: "Optional custom background color hex (e.g. #ffffff). Overrides the theme.",
      },
      text_color: {
        type: "string",
        description: "Optional custom text/label color hex (e.g. #1a1a1a). Overrides the theme.",
      },
      axis_color: {
        type: "string",
        description:
          "Optional custom axis line/tick color hex (e.g. #999999). Overrides the theme.",
      },
      split_line_color: {
        type: "string",
        description:
          "Optional custom grid split line color hex (e.g. #e8e8e8). Overrides the theme.",
      },
      palette: {
        type: "array",
        items: { type: "string" },
        description:
          "Optional custom color palette as an array of hex colors. Overrides the theme palette.",
      },
      primary_color: {
        type: "string",
        description:
          "Optional primary color hex. When palette is not provided, replaces the first theme color.",
      },
      language: {
        type: "string",
        enum: ["zh", "en", "auto"],
        description: "Language of the text. 'auto' detects from file content.",
        default: "auto",
      },
    },
    required: ["file_path"],
  },
};

export const wordcloudSchema = z.object({
  file_path: z.string().min(1),
  column: z.string().optional(),
  max_words: z.number().int().min(5).max(200).default(60),
  output_format: z.enum(["svg", "html", "png"]).default("svg"),
  width: z.number().int().min(200).max(2000).default(800),
  height: z.number().int().min(200).max(2000).default(500),
  theme: z
    .enum(["light", "dark", "colorful", "minimal", "professional", "retro", "science", "nature"])
    .default("nature"),
  font_family: z.string().optional(),
  background_color: z.string().optional(),
  text_color: z.string().optional(),
  axis_color: z.string().optional(),
  split_line_color: z.string().optional(),
  palette: z.array(z.string()).optional(),
  primary_color: z.string().optional(),
  language: z.enum(["zh", "en", "auto"]).default("auto"),
});

export async function runWordcloud(
  args: unknown,
  client: Hy3Client,
  onProgress?: ProgressReporter,
  signal?: AbortSignal,
  _onOutput?: (chunk: string) => void
) {
  const {
    file_path,
    column,
    max_words,
    output_format,
    width,
    height,
    theme,
    font_family,
    background_color,
    text_color,
    axis_color,
    split_line_color,
    palette,
    primary_color,
    language,
  } = wordcloudSchema.parse(args);

  await onProgress?.(10, 100);

  const themeOverrides = buildThemeOverrides(
    { background_color, text_color, axis_color, split_line_color, palette, primary_color },
    theme
  );
  const ext = extname(file_path);

  let text: string;
  if (ext === ".csv" || ext === ".json" || ext === ".jsonl" || ext === ".xlsx" || ext === ".xls") {
    const table = await loadDataTable(file_path);
    const targetColumn =
      column ||
      table.columns.find((c) => /text|content|comment|review|title|描述|内容|评论/i.test(c)) ||
      table.columns[0];
    text = table.rows.map((row) => String(row[targetColumn] ?? "")).join("\n");
  } else {
    const raw = await loadDataTable(file_path);
    text = raw.raw;
  }

  const resolvedLanguage = resolveLanguage(language, text);
  await onProgress?.(30, 100);

  const system =
    resolvedLanguage === "zh"
      ? `你是一位文本分析专家。请从以下文本中提取最有代表性的关键词及权重（0-100）。以纯 JSON 数组返回，格式：[{"word": "关键词", "weight": 80}, ...]。最多 ${max_words} 个词。不要输出任何额外文字。`
      : `You are a text-analysis expert. Extract the most representative keywords and their weights (0-100) from the text below. Return a pure JSON array: [{"word": "keyword", "weight": 80}, ...]. At most ${max_words} words. No extra text.`;

  let words: { word: string; weight: number }[];
  try {
    await onProgress?.(50, 100);
    const answer = await askHy3(client, system, sampleText(text), signal);
    words = JSON.parse(answer);
  } catch {
    words = fallbackWords(text, max_words, resolvedLanguage);
  }

  await onProgress?.(80, 100);
  const title = resolvedLanguage === "zh" ? "词云图" : "Word Cloud";
  const svg = renderWordcloudSvg(words, title, width, height, theme, font_family, themeOverrides);

  let content: string | Buffer;
  let fileExt: string;
  if (output_format === "html") {
    const wordcloudTheme = getTheme(theme, font_family, themeOverrides);
    content = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>${escapeHtml(title)}</title>
  <style>body{margin:0;padding:24px;background:${wordcloudTheme.backgroundColor};color:${wordcloudTheme.textColor};font-family:${wordcloudTheme.fontFamily};text-align:center;}</style>
</head>
<body>
  ${svg}
</body>
</html>`;
    fileExt = "html";
  } else if (output_format === "png") {
    content = await svgToPng(svg, width, height);
    fileExt = "png";
  } else {
    content = svg;
    fileExt = "svg";
  }

  const outputPath = await writeOutputFile(`wordcloud_${Date.now()}.${fileExt}`, content);

  await onProgress?.(100, 100);
  const formatLabel = output_format === "html" ? "HTML" : output_format === "png" ? "PNG" : "SVG";
  const summary =
    resolvedLanguage === "zh"
      ? `已生成 ${formatLabel} 词云图，共 ${words.length} 个关键词\n文件路径：${outputPath}`
      : `Generated ${formatLabel} word cloud with ${words.length} keywords\nFile path: ${outputPath}`;

  return { content: [{ type: "text" as const, text: summary }] };
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function fallbackWords(
  text: string,
  max: number,
  language: string
): { word: string; weight: number }[] {
  const isZh = /[\u4e00-\u9fa5]/.test(text);
  const tokens = isZh
    ? text.split(/[^\u4e00-\u9fa5a-zA-Z0-9]+/)
    : text.toLowerCase().split(/[^a-z0-9]+/);

  const stopwords = new Set(
    language === "zh"
      ? [
          "的",
          "了",
          "是",
          "在",
          "我",
          "有",
          "和",
          "就",
          "不",
          "人",
          "都",
          "一",
          "一个",
          "上",
          "也",
          "很",
          "到",
          "说",
          "要",
          "去",
          "你",
          "会",
          "着",
          "没有",
          "看",
          "好",
          "自己",
          "这",
          "那",
        ]
      : [
          "the",
          "a",
          "an",
          "is",
          "are",
          "was",
          "were",
          "be",
          "been",
          "being",
          "have",
          "has",
          "had",
          "do",
          "does",
          "did",
          "will",
          "would",
          "could",
          "should",
          "may",
          "might",
          "must",
          "shall",
          "can",
          "need",
          "dare",
          "ought",
          "used",
          "to",
          "of",
          "in",
          "for",
          "on",
          "with",
          "at",
          "by",
          "from",
          "as",
          "into",
          "through",
          "during",
          "before",
          "after",
          "above",
          "below",
          "between",
          "under",
          "again",
          "further",
          "then",
          "once",
          "here",
          "there",
          "when",
          "where",
          "why",
          "how",
          "all",
          "each",
          "few",
          "more",
          "most",
          "other",
          "some",
          "such",
          "no",
          "nor",
          "not",
          "only",
          "own",
          "same",
          "so",
          "than",
          "too",
          "very",
          "just",
          "and",
          "but",
          "if",
          "or",
          "because",
          "until",
          "while",
        ]
  );

  const counts = new Map<string, number>();
  for (const token of tokens) {
    const trimmed = token.trim();
    if (!trimmed || stopwords.has(trimmed)) continue;
    if (isZh && trimmed.length < 2) continue;
    counts.set(trimmed, (counts.get(trimmed) || 0) + 1);
  }

  const sorted = Array.from(counts.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, max);
  const maxCount = sorted[0]?.[1] || 1;
  return sorted.map(([word, count]) => ({
    word,
    weight: Math.round((count / maxCount) * 100),
  }));
}
