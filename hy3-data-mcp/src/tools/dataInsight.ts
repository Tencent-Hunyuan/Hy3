import { z } from "zod";
import { Hy3Client } from "../client.js";
import { askHy3, loadDataTable, resolveLanguage, tableSummary } from "../utils.js";
import type { ProgressReporter } from "./index.js";

export const dataInsightDefinition = {
  name: "hy3_data_insight",
  description:
    "Analyze a CSV/JSON file with Hy3 and produce textual insights, summaries, trend descriptions or answers to specific analytical questions.",
  inputSchema: {
    type: "object" as const,
    properties: {
      file_path: {
        type: "string",
        description: "Path to a CSV or JSON file.",
      },
      question: {
        type: "string",
        description: "Analytical question or task, e.g. 'Summarize the data' or 'Find outliers'.",
        default: "Summarize the data and highlight key insights",
      },
      language: {
        type: "string",
        enum: ["zh", "en", "auto"],
        description: "Language of the output. 'auto' detects from the question or data.",
        default: "auto",
      },
    },
    required: ["file_path"],
  },
};

export const dataInsightSchema = z.object({
  file_path: z.string().min(1),
  question: z.string().default("Summarize the data and highlight key insights"),
  language: z.enum(["zh", "en", "auto"]).default("auto"),
});

export async function runDataInsight(
  args: unknown,
  client: Hy3Client,
  onProgress?: ProgressReporter,
  signal?: AbortSignal,
  onOutput?: (chunk: string) => void
) {
  const { file_path, question, language } = dataInsightSchema.parse(args);

  await onProgress?.(10, 100);
  const table = await loadDataTable(file_path);
  await onProgress?.(30, 100);

  const resolvedLanguage = resolveLanguage(language, question, table.raw);

  const system =
    resolvedLanguage === "zh"
      ? "你是一位数据分析专家。请基于提供的数据进行严谨分析，给出清晰的结论、关键指标、趋势和异常点。如果数据不足以回答，请明确说明。"
      : "You are a data-analysis expert. Analyze the provided data rigorously and give clear conclusions, key metrics, trends and anomalies. State clearly if the data is insufficient.";

  const user =
    resolvedLanguage === "zh"
      ? `分析任务：${question}\n\n数据摘要：\n${tableSummary(table)}`
      : `Analysis task: ${question}\n\nData summary:\n${tableSummary(table)}`;

  await onProgress?.(50, 100);
  const answer = await askHy3(client, system, user, signal, onOutput);
  await onProgress?.(100, 100);
  return { content: [{ type: "text" as const, text: answer }] };
}
