import { z } from "zod";
import { Hy3Client } from "../client.js";
import { askHy3, resolveLanguage, sampleText, writeOutputFile } from "../utils.js";
import type { ProgressReporter } from "./index.js";

export const analyzeTextDefinition = {
  name: "hy3_analyze_text",
  description:
    "Analyze extracted document text with Hy3. Use this after hy3_extract_document for summarization, insight extraction, key metric extraction, or structured data conversion. If the user wants charts or dashboards, ask the model to return structured JSON/CSV data, save it to a file, and then call hy3_data_visualize, hy3_data_dashboard, or hy3_data_report.",
  inputSchema: {
    type: "object" as const,
    properties: {
      text: {
        type: "string",
        description: "Raw text extracted from a document (e.g. from hy3_extract_document).",
      },
      question: {
        type: "string",
        description:
          "What to do with the text, e.g. 'Summarize', 'Extract key risks', or 'Convert to structured JSON with columns and rows'.",
        default: "Summarize the text",
      },
      output_format: {
        type: "string",
        enum: ["text", "html", "json"],
        description:
          "'text' = plain text analysis; 'html' = formatted HTML report; 'json' = structured JSON output.",
        default: "text",
      },
      language: {
        type: "string",
        enum: ["zh", "en", "auto"],
        description: "Language of the output. 'auto' detects from the question or text.",
        default: "auto",
      },
    },
    required: ["text"],
  },
};

export const analyzeTextSchema = z.object({
  text: z.string().min(1),
  question: z.string().default("Summarize the text"),
  output_format: z.enum(["text", "html", "json"]).default("text"),
  language: z.enum(["zh", "en", "auto"]).default("auto"),
});

export async function runAnalyzeText(
  args: unknown,
  client: Hy3Client,
  onProgress?: ProgressReporter,
  signal?: AbortSignal,
  onOutput?: (chunk: string) => void
): Promise<{ content: Array<{ type: "text"; text: string }> }> {
  const { text, question, output_format, language } = analyzeTextSchema.parse(args);

  await onProgress?.(10, 100);
  const resolvedLanguage = resolveLanguage(language, question, text);

  const system =
    resolvedLanguage === "zh"
      ? `你是一位文档分析专家。请基于提供的文本内容完成用户指定的任务，给出结构清晰、重点突出的回答。如果内容不足以回答，请明确说明。当 output_format 为 json 时，必须返回合法 JSON；为 html 时，返回完整 HTML 页面；为 text 时，返回纯文本。`
      : `You are a document-analysis expert. Complete the user's task based on the provided text. Give a well-structured, focused answer. State clearly if the text is insufficient. When output_format is json, return valid JSON only; when html, return a complete HTML page; when text, return plain text.`;

  const outputFormatHint =
    resolvedLanguage === "zh"
      ? `输出格式要求：${output_format}`
      : `Required output format: ${output_format}`;

  const user =
    resolvedLanguage === "zh"
      ? `任务：${question}\n\n${outputFormatHint}\n\n文本内容（前 20000 字符）：\n${sampleText(text, 20000)}`
      : `Task: ${question}\n\n${outputFormatHint}\n\nText content (first 20000 chars):\n${sampleText(text, 20000)}`;

  await onProgress?.(40, 100);
  const answer = await askHy3(client, system, user, signal, onOutput);
  await onProgress?.(90, 100);

  if (output_format === "html") {
    const html = `<!DOCTYPE html>
<html lang="${resolvedLanguage === "zh" ? "zh-CN" : "en"}">
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
    <div>${answer
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\n/g, "<br/>")}</div>
  </div>
</body>
</html>`;
    const outputPath = await writeOutputFile(`analyze_text_${Date.now()}.html`, html);
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
