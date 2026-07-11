import { z } from "zod";
import { Hy3Client } from "../client.js";
import {
  askHy3,
  loadInputData,
  resolveLanguage,
  resolveOutputFilename,
  sampleText,
  tableSummary,
  writeOutputFile,
} from "../utils.js";
import type { ProgressReporter } from "./index.js";

export const analyzeDefinition = {
  name: "hy3_analyze",
  description:
    "Analyze text or structured data with Hy3. Accepts one of: text, data (JSON array string), data_file_path, or file_path. For text, summarize or extract insights. For data, analyze trends and metrics. Output can be text, json, or html.",
  inputSchema: {
    type: "object" as const,
    properties: {
      text: { type: "string", description: "Raw text to analyze." },
      data: { type: "string", description: "Inline structured data as a JSON array string." },
      data_file_path: { type: "string", description: "Path to a CSV/JSON/XLSX file." },
      file_path: { type: "string", description: "Alias for data_file_path." },
      question: {
        type: "string",
        description: "What to ask about the input.",
        default: "Summarize and extract key insights",
      },
      output_format: {
        type: "string",
        enum: ["text", "json", "html"],
        description: "Output format.",
        default: "text",
      },
      language: {
        type: "string",
        enum: ["zh", "en", "auto"],
        description: "Language of the output. 'auto' detects from input.",
        default: "auto",
      },
      output_filename: { type: "string", description: "Optional custom output file name (without extension)." },
    },
    required: [],
  },
};

export const analyzeSchema = z.object({
  text: z.string().optional(),
  data: z.string().optional(),
  data_file_path: z.string().optional(),
  file_path: z.string().optional(),
  question: z.string().default("Summarize and extract key insights"),
  output_format: z.enum(["text", "json", "html"]).default("text"),
  language: z.enum(["zh", "en", "auto"]).default("auto"),
  output_filename: z.string().optional(),
});

export async function runAnalyze(
  args: unknown,
  client: Hy3Client,
  onProgress?: ProgressReporter,
  signal?: AbortSignal,
  onOutput?: (chunk: string) => void
): Promise<{ content: Array<{ type: "text"; text: string }> }> {
  const { text, data, data_file_path, file_path, question, output_format, language, output_filename } =
    analyzeSchema.parse(args);

  const hasText = text && text.trim().length > 0;
  const hasData = data || data_file_path || file_path;

  if (!hasText && !hasData) {
    throw new Error("One of text, data, data_file_path, or file_path is required");
  }

  await onProgress?.(10, 100);

  let userContent: string;
  let resolvedLanguage: "zh" | "en";
  let mode: "text" | "data";

  if (hasText && !hasData) {
    mode = "text";
    const inputText = text!;
    resolvedLanguage = resolveLanguage(language, question, inputText);
    userContent =
      resolvedLanguage === "zh"
        ? `任务：${question}\n\n文本内容（前 20000 字符）：\n${sampleText(inputText, 20000)}`
        : `Task: ${question}\n\nText content (first 20000 chars):\n${sampleText(inputText, 20000)}`;
  } else {
    mode = "data";
    const table = await loadInputData({ data, data_file_path, file_path });
    resolvedLanguage = resolveLanguage(language, question, table.raw);
    userContent =
      resolvedLanguage === "zh"
        ? `分析任务：${question}\n\n数据摘要：\n${tableSummary(table)}`
        : `Analysis task: ${question}\n\nData summary:\n${tableSummary(table)}`;
  }

  const system =
    resolvedLanguage === "zh"
      ? mode === "text"
        ? `你是一位文档分析专家。请基于提供的内容完成用户指定的任务，给出结构清晰、重点突出的回答。如果内容不足以回答，请明确说明。当 output_format 为 json 时，必须返回合法 JSON；为 html 时，返回完整 HTML 页面；为 text 时，返回纯文本。`
        : `你是一位数据分析专家。请基于提供的数据进行严谨分析，给出清晰的结论、关键指标、趋势和异常点。如果数据不足以回答，请明确说明。当 output_format 为 json 时，必须返回合法 JSON；为 html 时，返回完整 HTML 页面；为 text 时，返回纯文本。`
      : mode === "text"
      ? `You are a document-analysis expert. Complete the user's task based on the provided content. Give a well-structured, focused answer. State clearly if the content is insufficient. When output_format is json, return valid JSON only; when html, return a complete HTML page; when text, return plain text.`
      : `You are a data-analysis expert. Analyze the provided data rigorously and give clear conclusions, key metrics, trends and anomalies. State clearly if the data is insufficient. When output_format is json, return valid JSON only; when html, return a complete HTML page; when text, return plain text.`;

  const outputFormatHint =
    resolvedLanguage === "zh" ? `输出格式要求：${output_format}` : `Required output format: ${output_format}`;

  await onProgress?.(40, 100);
  const answer = await askHy3(client, system, `${userContent}\n\n${outputFormatHint}`, signal, onOutput);
  await onProgress?.(90, 100);

  if (output_format === "html") {
    const htmlContent = normalizeHtmlAnswer(answer, question, resolvedLanguage);
    const outputPath = await writeOutputFile(
      resolveOutputFilename(output_filename, `analyze_${Date.now()}`, "html"),
      htmlContent
    );
    await onProgress?.(100, 100);
    return {
      content: [
        {
          type: "text" as const,
          text:
            resolvedLanguage === "zh"
              ? `已生成 HTML 分析报告\n文件路径：${outputPath}`
              : `Generated HTML analysis report\nFile path: ${outputPath}`,
        },
      ],
    };
  }

  await onProgress?.(100, 100);
  return { content: [{ type: "text" as const, text: answer }] };
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function normalizeHtmlAnswer(answer: string, question: string, language: "zh" | "en"): string {
  if (isCompleteHtml(answer)) {
    return answer;
  }
  if (looksLikeEncodedHtml(answer)) {
    const decoded = decodeHtmlEntities(answer);
    if (isCompleteHtml(decoded)) {
      return decoded;
    }
  }
  return wrapHtmlAnswer(answer, question, language);
}

function wrapHtmlAnswer(answer: string, question: string, language: "zh" | "en"): string {
  return `<!DOCTYPE html>
<html lang="${language === "zh" ? "zh-CN" : "en"}">
<head>
  <meta charset="UTF-8">
  <title>${escapeHtml(question)}</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 800px; margin: 40px auto; padding: 24px; background: #f6f8fa; color: #24292f; line-height: 1.6; }
    .container { background: #fff; border-radius: 12px; padding: 32px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    h1 { font-size: 22px; margin-bottom: 16px; }
    pre { background: #f6f8fa; padding: 12px; border-radius: 6px; overflow-x: auto; }
  </style>
</head>
<body>
  <div class="container">
    <h1>${escapeHtml(question)}</h1>
    <div>${answer.replace(/\n/g, "<br/>")}</div>
  </div>
</body>
</html>`;
}

function looksLikeEncodedHtml(text: string): boolean {
  return /&lt;|&gt;|&quot;|&#39;|&amp;lt;/.test(text);
}

function decodeHtmlEntities(text: string): string {
  return text
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&amp;/g, "&");
}

function isCompleteHtml(text: string): boolean {
  return /^\s*<(!DOCTYPE|html)/i.test(text);
}
