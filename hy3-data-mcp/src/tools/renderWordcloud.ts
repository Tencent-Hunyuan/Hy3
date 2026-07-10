import { z } from "zod";
import { extname } from "path";
import { renderWordcloudSvg } from "../viz/wordcloud.js";
import { svgToPng } from "../viz/png.js";
import { getTheme } from "../viz/themes.js";
import { buildThemeOverrides, loadDataTable, loadInputText, resolveLanguage, selectTextColumn, writeOutputFile } from "../utils.js";
import type { ProgressReporter } from "./index.js";

export const renderWordcloudDefinition = {
  name: "hy3_render_wordcloud",
  description:
    "Render a word cloud directly from explicit words or raw text. Does NOT call LLM. Accepts either words (JSON array of {word, weight}) or text/file_path for raw text counting.",
  inputSchema: {
    type: "object" as const,
    properties: {
      words: {
        type: "string",
        description: "JSON array string of {word, weight} objects.",
      },
      text: { type: "string", description: "Raw text; keywords will be counted automatically." },
      file_path: { type: "string", description: "Path to a text file; keywords will be counted automatically." },
      max_words: { type: "number", description: "Maximum number of words.", default: 60 },
      output_format: { type: "string", enum: ["svg", "html", "png"], default: "svg" },
      width: { type: "number", default: 800 },
      height: { type: "number", default: 500 },
      theme: { type: "string", enum: ["light", "dark", "colorful", "minimal", "professional", "premium", "retro", "science", "nature"], default: "nature" },
      font_family: { type: "string" },
      background_color: { type: "string" },
      text_color: { type: "string" },
      axis_color: { type: "string" },
      split_line_color: { type: "string" },
      palette: { type: "array", items: { type: "string" } },
      primary_color: { type: "string" },
      language: { type: "string", enum: ["zh", "en", "auto"], default: "auto" },
    },
    required: [],
  },
};

export const renderWordcloudSchema = z.object({
  words: z.string().optional(),
  text: z.string().optional(),
  file_path: z.string().optional(),
  max_words: z.number().int().min(5).max(200).default(60),
  output_format: z.enum(["svg", "html", "png"]).default("svg"),
  width: z.number().int().min(200).max(2000).default(800),
  height: z.number().int().min(200).max(2000).default(500),
  theme: z.enum(["light", "dark", "colorful", "minimal", "professional", "premium", "retro", "science", "nature"]).default("nature"),
  font_family: z.string().optional(),
  background_color: z.string().optional(),
  text_color: z.string().optional(),
  axis_color: z.string().optional(),
  split_line_color: z.string().optional(),
  palette: z.array(z.string()).optional(),
  primary_color: z.string().optional(),
  language: z.enum(["zh", "en", "auto"]).default("auto"),
});

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
          "的", "了", "是", "在", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这", "那",
        ]
      : [
          "the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "could", "should", "may", "might", "must", "shall", "can", "need", "dare", "ought", "used", "to", "of", "in", "for", "on", "with", "at", "by", "from", "as", "into", "through", "during", "before", "after", "above", "below", "between", "under", "again", "further", "then", "once", "here", "there", "when", "where", "why", "how", "all", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "just", "and", "but", "if", "or", "because", "until", "while",
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

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

export async function runRenderWordcloud(
  args: unknown,
  onProgress?: ProgressReporter
): Promise<{ content: Array<{ type: "text"; text: string }> }> {
  const {
    words,
    text,
    file_path,
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
  } = renderWordcloudSchema.parse(args);

  if (!words && !text && !file_path) {
    throw new Error("One of words, text, or file_path is required");
  }

  await onProgress?.(10, 100);

  const themeOverrides = buildThemeOverrides(
    { background_color, text_color, axis_color, split_line_color, palette, primary_color },
    theme
  );

  let wordList: { word: string; weight: number }[];
  let resolvedLanguage: "zh" | "en";

  if (words) {
    wordList = JSON.parse(words);
    resolvedLanguage = resolveLanguage(language);
  } else {
    let rawText: string;
    if (text) {
      rawText = text;
    } else {
      const ext = extname(file_path!);
      if (ext === ".csv" || ext === ".json" || ext === ".jsonl" || ext === ".xlsx" || ext === ".xls") {
        const table = await loadDataTable(file_path!);
        const targetColumn = selectTextColumn(table.columns, table.rows) || table.columns[0];
        rawText = table.rows.map((row) => String(row[targetColumn] ?? "")).join("\n");
      } else {
        rawText = await loadInputText({ file_path: file_path! });
      }
    }
    resolvedLanguage = resolveLanguage(language, rawText);
    wordList = fallbackWords(rawText, max_words, resolvedLanguage);
  }

  await onProgress?.(60, 100);
  const title = resolvedLanguage === "zh" ? "词云图" : "Word Cloud";
  const svg = renderWordcloudSvg(wordList, title, width, height, theme, font_family, themeOverrides);

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
      ? `已生成 ${formatLabel} 词云图，共 ${wordList.length} 个关键词\n文件路径：${outputPath}`
      : `Generated ${formatLabel} word cloud with ${wordList.length} keywords\nFile path: ${outputPath}`;

  return { content: [{ type: "text" as const, text: summary }] };
}
