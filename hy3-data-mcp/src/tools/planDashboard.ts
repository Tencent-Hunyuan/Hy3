import { z } from "zod";
import { Hy3Client } from "../client.js";
import {
  askHy3,
  DataTable,
  loadDataTable,
  parseInlineData,
  resolveLanguage,
  tableSummary,
} from "../utils.js";
import type { ProgressReporter } from "./index.js";

export const planDashboardDefinition = {
  name: "hy3_plan_dashboard",
  description:
    "Design a dashboard layout from structured data. Hy3 chooses chart types, columns, and titles and returns a pure JSON design. Use the output with hy3_render_dashboard to actually render the dashboard.",
  inputSchema: {
    type: "object" as const,
    properties: {
      file_paths: {
        type: "array",
        items: { type: "string" },
        description: "List of CSV or JSON files to include in the dashboard. Either this or `data` is required.",
      },
      data: {
        type: "string",
        description: "Inline data as a JSON array string, e.g. '[{\"month\":\"Jan\",\"sales\":100},...]'. Either this or `file_paths`/`data_file_path` is required.",
      },
      data_file_path: {
        type: "string",
        description: "Path to a CSV/JSON/XLSX file. Either this or `data`/`file_paths` is required.",
      },
      title: {
        type: "string",
        description: "Dashboard title. Leave empty to let Hy3 generate one.",
      },
      layout: {
        type: "string",
        enum: ["grid", "rows", "columns", "hero", "compact"],
        description: "Preferred dashboard layout style.",
        default: "grid",
      },
      theme: {
        type: "string",
        enum: ["light", "dark", "colorful", "minimal", "professional", "premium", "retro", "science", "nature"],
        description: "Dashboard color theme.",
        default: "nature",
      },
      language: {
        type: "string",
        enum: ["zh", "en", "auto"],
        description: "Language of titles and labels.",
        default: "auto",
      },
    },
    required: [],
  },
};

export const planDashboardSchema = z.object({
  file_paths: z.array(z.string().min(1)).optional(),
  data_file_path: z.string().optional(),
  data: z.string().optional(),
  title: z.string().optional(),
  layout: z.enum(["grid", "rows", "columns", "hero", "compact"]).default("grid"),
  theme: z.enum(["light", "dark", "colorful", "minimal", "professional", "premium", "retro", "science", "nature"]).default("nature"),
  language: z.enum(["zh", "en", "auto"]).default("auto"),
});

export type DashboardDesign = {
  title: string;
  layout: "grid" | "rows" | "columns" | "hero" | "compact";
  theme?: string;
  charts: Array<{
    file_index: number;
    chart_type: string;
    x_column: string;
    y_column: string;
    value_column?: string;
    group_column?: string;
    size_column?: string;
    z_column?: string;
    title: string;
  }>;
};

export async function runPlanDashboard(
  args: unknown,
  client: Hy3Client,
  onProgress?: ProgressReporter,
  signal?: AbortSignal,
  _onOutput?: (chunk: string) => void
): Promise<{ content: Array<{ type: "text"; text: string }> }> {
  const { file_paths, data_file_path, data, title, layout, language, theme } = planDashboardSchema.parse(args);

  if ((!file_paths || file_paths.length === 0) && !data_file_path && (!data || data.trim().length === 0)) {
    throw new Error("One of file_paths, data_file_path, or data is required");
  }

  await onProgress?.(10, 100);

  const tables: { path: string; table: DataTable }[] = [];
  if (data) {
    tables.push({ path: "<inline-data>", table: parseInlineData(data) });
  }
  if (data_file_path) {
    tables.push({ path: data_file_path, table: await loadDataTable(data_file_path) });
  }
  for (const path of file_paths ?? []) {
    tables.push({ path, table: await loadDataTable(path) });
  }
  await onProgress?.(30, 100);

  const resolvedLanguage = resolveLanguage(language, title);

  const summaryText = tables
    .map(({ path, table }) => `File: ${path}\n${tableSummary(table)}`)
    .join("\n\n");

  await onProgress?.(50, 100);

  const system =
    resolvedLanguage === "zh"
      ? `你是一位数据大屏设计专家。请基于提供的数据文件，设计一个可视化大屏布局。支持的图表类型：bar、line、area、pie、donut、rose、scatter、bubble、scatter_trend、radar、heatmap、funnel、sankey、treemap、sunburst、gauge、histogram、boxplot、stacked_bar、grouped_bar、bar3d、scatter3d、line3d、line_bar、area_bar、dual_axis、stacked_area、grouped_line。以纯 JSON 返回：{"title": string, "layout": "${layout}", "charts": [{"file_index": number, "chart_type": string, "x_column": string, "y_column": string, "value_column": string?, "group_column": string?, "size_column": string?, "z_column": string?, "title": string}] }。不要输出任何额外文字。`
      : `You are a dashboard design expert. Based on the provided data files, design a visualization dashboard layout. Supported chart types: bar, line, area, pie, donut, rose, scatter, bubble, scatter_trend, radar, heatmap, funnel, sankey, treemap, sunburst, gauge, histogram, boxplot, stacked_bar, grouped_bar, bar3d, scatter3d, line3d, line_bar, area_bar, dual_axis, stacked_area, grouped_line. Return pure JSON: {"title": string, "layout": "${layout}", "charts": [{"file_index": number, "chart_type": string, "x_column": string, "y_column": string, "value_column": string?, "group_column": string?, "size_column": string?, "z_column": string?, "title": string}] }. No extra text.`;

  let design: DashboardDesign;
  try {
    await onProgress?.(70, 100);
    const answer = await askHy3(client, system, summaryText, signal, _onOutput);
    design = JSON.parse(answer) as DashboardDesign;
  } catch {
    design = {
      title: title || (resolvedLanguage === "zh" ? "数据大屏" : "Data Dashboard"),
      layout,
      charts: tables.slice(0, 1).map(({ table }, i) => ({
        file_index: i,
        chart_type: "bar",
        x_column: table.columns[0],
        y_column: table.columns[1] || table.columns[0],
        title: resolvedLanguage === "zh" ? "概览" : "Overview",
      })),
    };
  }

  if (title) design.title = title;
  if (!design.layout) design.layout = layout;
  if (!design.theme) design.theme = theme;
  await onProgress?.(100, 100);

  return { content: [{ type: "text", text: JSON.stringify(design, null, 2) }] };
}
