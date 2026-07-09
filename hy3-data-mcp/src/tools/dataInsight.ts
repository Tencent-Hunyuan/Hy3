import { z } from "zod";
import { Hy3Client } from "../client.js";
import { askHy3, loadDataTable, tableSummary } from "../utils.js";

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
        enum: ["zh", "en"],
        description: "Language of the output.",
        default: "zh",
      },
    },
    required: ["file_path"],
  },
};

const dataInsightSchema = z.object({
  file_path: z.string().min(1),
  question: z.string().default("Summarize the data and highlight key insights"),
  language: z.enum(["zh", "en"]).default("zh"),
});

export async function runDataInsight(args: unknown, client: Hy3Client) {
  const { file_path, question, language } = dataInsightSchema.parse(args);
  const table = await loadDataTable(file_path);

  const system =
    language === "zh"
      ? "你是一位数据分析专家。请基于提供的数据进行严谨分析，给出清晰的结论、关键指标、趋势和异常点。如果数据不足以回答，请明确说明。"
      : "You are a data-analysis expert. Analyze the provided data rigorously and give clear conclusions, key metrics, trends and anomalies. State clearly if the data is insufficient.";

  const user =
    language === "zh"
      ? `分析任务：${question}\n\n数据摘要：\n${tableSummary(table)}`
      : `Analysis task: ${question}\n\nData summary:\n${tableSummary(table)}`;

  const answer = await askHy3(client, system, user);
  return { content: [{ type: "text" as const, text: answer }] };
}
