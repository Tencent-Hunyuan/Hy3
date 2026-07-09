import { z } from "zod";
import { Hy3Client } from "../client.js";
import { extractTextFromDocument } from "../documents.js";
import { askHy3, sampleText, writeOutputFile } from "../utils.js";

export const documentSummaryDefinition = {
  name: "hy3_document_summary",
  description:
    "Summarize or analyze a PDF, Word (DOCX), TXT, CSV, JSON or XLSX document using Hy3. Optionally outputs the result as a formatted HTML report.",
  inputSchema: {
    type: "object" as const,
    properties: {
      file_path: {
        type: "string",
        description: "Path to a PDF, DOCX, TXT, CSV, JSON or XLSX file.",
      },
      question: {
        type: "string",
        description: "What to do with the document, e.g. 'Summarize' or 'Extract key risks'.",
        default: "Summarize the document",
      },
      output_format: {
        type: "string",
        enum: ["text", "html"],
        description: "'text' = plain text; 'html' = formatted HTML report.",
        default: "text",
      },
      language: {
        type: "string",
        enum: ["zh", "en"],
        description: "Language of the output.",
        default: "zh",
      },
    },
    required: ["file_path"],
  },
};

const documentSummarySchema = z.object({
  file_path: z.string().min(1),
  question: z.string().default("Summarize the document"),
  output_format: z.enum(["text", "html"]).default("text"),
  language: z.enum(["zh", "en"]).default("zh"),
});

export async function runDocumentSummary(args: unknown, client: Hy3Client) {
  const { file_path, question, output_format, language } = documentSummarySchema.parse(args);

  const text = await extractTextFromDocument(file_path);
  if (!text.trim()) {
    throw new Error("No text could be extracted from the document.");
  }

  const system =
    language === "zh"
      ? "你是一位文档分析专家。请基于提供的文档内容完成用户指定的任务，给出结构清晰、重点突出的回答。如果文档内容不足以回答，请明确说明。"
      : "You are a document-analysis expert. Complete the user's task based on the provided document content. Give a well-structured, focused answer. State clearly if the document is insufficient.";

  const user =
    language === "zh"
      ? `任务：${question}\n\n文档内容（前 20000 字符）：\n${sampleText(text, 20000)}`
      : `Task: ${question}\n\nDocument content (first 20000 chars):\n${sampleText(text, 20000)}`;

  const answer = await askHy3(client, system, user);

  if (output_format === "html") {
    const html = `<!DOCTYPE html>
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
    <div>${answer
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\n/g, "<br/>")}</div>
  </div>
</body>
</html>`;
    const outputPath = await writeOutputFile(`document_summary_${Date.now()}.html`, html);
    return {
      content: [
        {
          type: "text" as const,
          text:
            language === "zh"
              ? `已生成 HTML 文档分析报告\n文件路径：${outputPath}`
              : `Generated HTML document analysis report\nFile path: ${outputPath}`,
        },
      ],
    };
  }

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
