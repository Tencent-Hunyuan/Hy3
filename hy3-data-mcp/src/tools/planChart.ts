import { z } from "zod";
import { Hy3Client } from "../client.js";
import { askHy3Json } from "../llm-utils.js";
import { dataInputShape, languageSchema, rawDataInputProperties, rawLanguageProperty } from "../schemas.js";
import { loadInputData, resolveLanguage, tableSummary, validateDataTable } from "../utils.js";
import type { ChartType } from "../viz/echarts.js";
import type { ProgressReporter } from "./index.js";

const SUPPORTED_CHART_TYPES: ChartType[] = [
  "bar",
  "line",
  "area",
  "pie",
  "donut",
  "rose",
  "scatter",
  "bubble",
  "scatter_trend",
  "radar",
  "heatmap",
  "funnel",
  "sankey",
  "treemap",
  "sunburst",
  "gauge",
  "histogram",
  "boxplot",
  "candlestick",
  "stacked_bar",
  "grouped_bar",
  "bar3d",
  "scatter3d",
  "line3d",
  "line_bar",
  "area_bar",
  "dual_axis",
  "stacked_area",
  "grouped_line",
];

export const planChartDefinition = {
  name: "hy3_plan_chart",
  description:
    "Use Hy3 to plan the best chart configuration (type, columns, title) from structured data. Returns JSON that can be passed directly to hy3_render_chart.",
  inputSchema: {
    type: "object" as const,
    properties: {
      ...rawDataInputProperties,
      question: {
        type: "string",
        description: "What the chart should show.",
        default: "Recommend a chart",
      },
      chart_type_hint: {
        type: "string",
        description: "Optional preferred chart type.",
      },
      ...rawLanguageProperty("Language of the output."),
    },
    required: [],
  },
};

export const planChartSchema = z
  .object({
    ...dataInputShape,
    question: z.string().default("Recommend a chart"),
    chart_type_hint: z.string().optional(),
    language: languageSchema,
  })
  .refine(
    (args) => Boolean(args.data?.trim()) || Boolean(args.data_file_path?.trim()) || Boolean(args.file_path?.trim()),
    { message: "One of data, data_file_path, or file_path is required" }
  );

export interface ChartPlan {
  chart_type: ChartType;
  x_column: string;
  y_column: string;
  value_column?: string;
  open_column?: string;
  close_column?: string;
  high_column?: string;
  low_column?: string;
  group_column?: string;
  size_column?: string;
  z_column?: string;
  title: string;
  theme?: string;
  _warning?: string;
}

const chartPlanOutputSchema = z.object({
  chart_type: z.enum(SUPPORTED_CHART_TYPES as [string, ...string[]]),
  x_column: z.string(),
  y_column: z.string(),
  value_column: z.string().optional(),
  open_column: z.string().optional(),
  close_column: z.string().optional(),
  high_column: z.string().optional(),
  low_column: z.string().optional(),
  group_column: z.string().optional(),
  size_column: z.string().optional(),
  z_column: z.string().optional(),
  title: z.string().optional(),
  theme: z.string().optional(),
});

export async function runPlanChart(
  args: unknown,
  client: Hy3Client,
  onProgress?: ProgressReporter,
  signal?: AbortSignal,
  onOutput?: (chunk: string) => void
): Promise<{ content: Array<{ type: "text"; text: string }> }> {
  const { data, data_file_path, file_path, question, chart_type_hint, language } =
    planChartSchema.parse(args);

  await onProgress?.(10, 100);
  const table = await loadInputData({ data, data_file_path, file_path });
  await onProgress?.(30, 100);
  validateDataTable(table);

  const resolvedLanguage = resolveLanguage(language, question, table.raw);

  const system =
    resolvedLanguage === "zh"
      ? `你是一位数据可视化专家。请根据图表类型推荐合适的列，并以纯 JSON 返回：{"chart_type": string, "x_column": string, "y_column": string, "value_column": string?, "open_column": string?, "close_column": string?, "high_column": string?, "low_column": string?, "group_column": string?, "size_column": string?, "z_column": string?, "title": string, "theme": string?}。支持的图表类型：${SUPPORTED_CHART_TYPES.join(
          ", "
        )}。说明：普通图表使用 x_column/y_column；桑基图使用 x_column 作为 source、y_column 作为 target、value_column 作为流量；矩形树图/旭日图使用 x_column 作为名称、y_column 作为数值；K 线图使用 open_column/close_column/low_column/high_column；堆叠/分组柱状图使用 group_column；气泡图使用 size_column 控制点大小；3D 散点/折线使用 z_column 作为第三维；复合图（line_bar、area_bar、dual_axis）使用 value_column 作为第二指标；stacked_area 与 grouped_line 使用 group_column 分组；直方图自动对数值列分箱。不要输出任何额外文字。`
      : `You are a data visualization expert. Recommend suitable columns for the requested chart type and return only pure JSON: {"chart_type": string, "x_column": string, "y_column": string, "value_column": string?, "open_column": string?, "close_column": string?, "high_column": string?, "low_column": string?, "group_column": string?, "size_column": string?, "z_column": string?, "title": string, "theme": string?}. Supported chart types: ${SUPPORTED_CHART_TYPES.join(
          ", "
        )}. Notes: regular charts use x_column/y_column; sankey uses x_column as source, y_column as target, value_column as weight; treemap/sunburst use x_column as name and y_column as value; candlestick uses open_column/close_column/low_column/high_column; stacked/grouped bar uses group_column; bubble uses size_column for point size; 3D scatter/line use z_column as the third dimension; composite charts (line_bar, area_bar, dual_axis) use value_column as the second metric; stacked_area and grouped_line use group_column to split series; histogram auto-bins a numeric column. No extra text.`;

  const user =
    resolvedLanguage === "zh"
      ? `用户需求：${question}\n用户偏好的图表类型：${chart_type_hint || "（未指定）"}\n数据摘要：\n${tableSummary(table)}`
      : `User need: ${question}\nPreferred chart type: ${chart_type_hint || "(none)"}\nData summary:\n${tableSummary(table)}`;

  await onProgress?.(60, 100);

  let plan: ChartPlan;
  try {
    const parsed = await askHy3Json(client, system, user, chartPlanOutputSchema, { signal, onToken: onOutput });
    const chartType = parsed.data.chart_type as ChartType;
    const xColumn = parsed.data.x_column || table.columns[0];
    const yColumn = parsed.data.y_column || table.columns[1] || table.columns[0];
    plan = {
      chart_type: chartType,
      x_column: xColumn,
      y_column: yColumn,
      value_column: parsed.data.value_column || (["sunburst", "treemap"].includes(chartType) ? yColumn : undefined),
      open_column: parsed.data.open_column,
      close_column: parsed.data.close_column,
      high_column: parsed.data.high_column,
      low_column: parsed.data.low_column,
      group_column: parsed.data.group_column,
      size_column: parsed.data.size_column,
      z_column: parsed.data.z_column,
      title: parsed.data.title || (resolvedLanguage === "zh" ? "数据图表" : "Data Chart"),
      theme: parsed.data.theme,
    };
  } catch {
    plan = {
      chart_type: "bar",
      x_column: table.columns[0],
      y_column: table.columns[1] || table.columns[0],
      title: resolvedLanguage === "zh" ? "数据图表" : "Data Chart",
      _warning: resolvedLanguage === "zh" ? "模型输出解析失败，已使用默认柱状图方案。" : "Model output could not be parsed; using default bar chart.",
    };
  }

  await onProgress?.(100, 100);
  return { content: [{ type: "text" as const, text: JSON.stringify(plan, null, 2) }] };
}
