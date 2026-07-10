import { z } from "zod";
import { extname } from "path";
import { Hy3Client } from "../client.js";
import { askHy3, loadDataTable, loadInputText, resolveLanguage, sampleText } from "../utils.js";
import type { ProgressReporter } from "./index.js";

export const planWordcloudDefinition = {
  name: "hy3_plan_wordcloud",
  description:
    "Use Hy3 to extract the most representative keywords and weights from text or a file. Returns a JSON array of {word, weight} that can be passed to hy3_render_wordcloud.",
  inputSchema: {
    type: "object" as const,
    properties: {
      text: { type: "string", description: "Raw text to analyze." },
      file_path: { type: "string", description: "Path to a text, CSV, JSON or XLSX file." },
      max_words: {
        type: "number",
        description: "Maximum number of words.",
        default: 60,
      },
      language: {
        type: "string",
        enum: ["zh", "en", "auto"],
        description: "Language of the text.",
        default: "auto",
      },
    },
    required: [],
  },
};

export const planWordcloudSchema = z.object({
  text: z.string().optional(),
  file_path: z.string().optional(),
  max_words: z.number().int().min(5).max(200).default(60),
  language: z.enum(["zh", "en", "auto"]).default("auto"),
});

export interface WordcloudPlan {
  words: { word: string; weight: number }[];
}

export async function runPlanWordcloud(
  args: unknown,
  client: Hy3Client,
  onProgress?: ProgressReporter,
  signal?: AbortSignal,
  onOutput?: (chunk: string) => void
): Promise<{ content: Array<{ type: "text"; text: string }> }> {
  const { text, file_path, max_words, language } = planWordcloudSchema.parse(args);

  if (!text && !file_path) {
    throw new Error("One of text or file_path is required");
  }

  await onProgress?.(10, 100);

  let inputText: string;
  if (text) {
    inputText = text;
  } else {
    const ext = extname(file_path!);
    if (ext === ".csv" || ext === ".json" || ext === ".jsonl" || ext === ".xlsx" || ext === ".xls") {
      const table = await loadDataTable(file_path!);
      const targetColumn =
        table.columns.find((c) => /text|content|comment|review|title|描述|内容|评论/i.test(c)) ||
        table.columns[0];
      inputText = table.rows.map((row) => String(row[targetColumn] ?? "")).join("\n");
    } else {
      inputText = await loadInputText({ file_path: file_path! });
    }
  }

  const resolvedLanguage = resolveLanguage(language, inputText);
  await onProgress?.(30, 100);

  const system =
    resolvedLanguage === "zh"
      ? `你是一位文本分析专家。请从以下文本中提取最有代表性的关键词及权重（0-100）。以纯 JSON 数组返回，格式：[{"word": "关键词", "weight": 80}, ...]。最多 ${max_words} 个词。不要输出任何额外文字。`
      : `You are a text-analysis expert. Extract the most representative keywords and their weights (0-100) from the text below. Return a pure JSON array: [{"word": "keyword", "weight": 80}, ...]. At most ${max_words} words. No extra text.`;

  await onProgress?.(60, 100);
  const answer = await askHy3(client, system, sampleText(inputText), signal, onOutput);
  await onProgress?.(90, 100);

  let words: { word: string; weight: number }[];
  try {
    words = JSON.parse(answer);
    if (!Array.isArray(words)) words = [];
  } catch {
    words = [];
  }

  await onProgress?.(100, 100);
  return { content: [{ type: "text" as const, text: JSON.stringify({ words }, null, 2) }] };
}
