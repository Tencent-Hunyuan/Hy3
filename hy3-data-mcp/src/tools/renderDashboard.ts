import { z } from "zod";
import { renderDashboardHtml, renderDashboardPng, type ChartType } from "../viz/echarts.js";
import { buildThemeOverrides, DataTable, loadDataTable, parseInlineData, resolveLanguage, writeOutputFile } from "../utils.js";
import type { ProgressReporter } from "./index.js";


export const renderDashboardDefinition = {
  name: "hy3_render_dashboard",
  description:
    "Render a dashboard design (from hy3_design_dashboard) into an interactive HTML page or a PNG composite image. Requires the same file_paths and a JSON design object.",
  inputSchema: {
    type: "object" as const,
    properties: {
      file_paths: {
        type: "array",
        items: { type: "string" },
        description: "List of CSV or JSON files referenced by the design. Either this or `data` is required. Must match the order used in hy3_design_dashboard.",
      },
      data: {
        type: "string",
        description: "Inline data as a JSON array string. Either this or `file_paths` is required. If both are provided, inline data is placed at index 0.",
      },
      design: {
        type: "object",
        description: "Dashboard design JSON produced by hy3_design_dashboard.",
        properties: {
          title: { type: "string" },
          layout: { type: "string", enum: ["grid", "rows", "columns", "hero", "compact"] },
          charts: {
            type: "array",
            items: {
              type: "object",
              properties: {
                file_index: { type: "number" },
                chart_type: { type: "string" },
                x_column: { type: "string" },
                y_column: { type: "string" },
                value_column: { type: "string" },
                group_column: { type: "string" },
                size_column: { type: "string" },
                z_column: { type: "string" },
                title: { type: "string" },
              },
              required: ["file_index", "chart_type", "x_column", "y_column", "title"],
            },
          },
        },
        required: ["title", "charts"],
      },
      output_format: {
        type: "string",
        enum: ["html", "png"],
        description: "'html' = interactive dashboard page; 'png' = static composite image.",
        default: "html",
      },
      title: {
        type: "string",
        description: "Optional title override. If omitted, uses design.title.",
      },
      theme: {
        type: "string",
        enum: ["light", "dark", "colorful", "minimal", "professional", "retro", "science", "nature"],
        description: "Dashboard color theme.",
        default: "nature",
      },
      font_family: {
        type: "string",
        description: "Custom font family for titles and labels.",
      },
      background_color: { type: "string", description: "Optional background color hex." },
      text_color: { type: "string", description: "Optional text/label color hex." },
      axis_color: { type: "string", description: "Optional axis line/tick color hex." },
      split_line_color: { type: "string", description: "Optional grid split line color hex." },
      palette: {
        type: "array",
        items: { type: "string" },
        description: "Optional custom color palette.",
      },
      primary_color: { type: "string", description: "Optional primary color hex." },
      layout: {
        type: "string",
        enum: ["grid", "rows", "columns", "hero", "compact"],
        description: "Optional layout override. If omitted, uses design.layout.",
      },
      language: {
        type: "string",
        enum: ["zh", "en", "auto"],
        description: "Language of the returned summary.",
        default: "auto",
      },
    },
    required: ["design"],
  },
};

const chartDesignSchema = z.object({
  file_index: z.number().int().min(0),
  chart_type: z.string(),
  x_column: z.string(),
  y_column: z.string(),
  value_column: z.string().optional(),
  group_column: z.string().optional(),
  size_column: z.string().optional(),
  z_column: z.string().optional(),
  title: z.string(),
});

export const renderDashboardSchema = z.object({
  file_paths: z.array(z.string().min(1)).optional(),
  data: z.string().optional(),
  design: z.object({
    title: z.string(),
    layout: z.enum(["grid", "rows", "columns", "hero", "compact"]).optional(),
    charts: z.array(chartDesignSchema).min(1),
  }),
  output_format: z.enum(["html", "png"]).default("html"),
  title: z.string().optional(),
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
  layout: z.enum(["grid", "rows", "columns", "hero", "compact"]).optional(),
  language: z.enum(["zh", "en", "auto"]).default("auto"),
});

export async function runRenderDashboard(
  args: unknown,
  onProgress?: ProgressReporter
): Promise<{ content: Array<{ type: "text"; text: string }> }> {
  const {
    file_paths,
    data,
    design,
    output_format,
    title,
    theme,
    font_family,
    background_color,
    text_color,
    axis_color,
    split_line_color,
    palette,
    primary_color,
    layout,
    language,
  } = renderDashboardSchema.parse(args);

  if ((!file_paths || file_paths.length === 0) && (!data || data.trim().length === 0)) {
    throw new Error("Either file_paths or data is required");
  }

  await onProgress?.(10, 100);

  const themeOverrides = buildThemeOverrides(
    { background_color, text_color, axis_color, split_line_color, palette, primary_color },
    theme
  );

  const tables: { path: string; table: DataTable }[] = [];
  if (data) {
    tables.push({ path: "<inline-data>", table: parseInlineData(data) });
  }
  for (const path of file_paths ?? []) {
    tables.push({ path, table: await loadDataTable(path) });
  }
  await onProgress?.(30, 100);

  const resolvedLanguage = resolveLanguage(language, title || design.title);
  const resolvedLayout = layout || design.layout || "grid";
  const resolvedTitle = title || design.title;

  const chartInputs = design.charts
    .map((chart) => {
      const source = tables[chart.file_index] ?? tables[0];
      if (!source) return null;
      return {
        chartType: chart.chart_type as ChartType,
        table: source.table,
        config: {
          x_column: chart.x_column,
          y_column: chart.y_column,
          value_column: chart.value_column,
          group_column: chart.group_column,
          size_column: chart.size_column,
          z_column: chart.z_column,
          title: chart.title,
        },
      };
    })
    .filter(Boolean) as Array<{
    chartType: ChartType;
    table: DataTable;
    config: {
      x_column: string;
      y_column: string;
      value_column?: string;
      group_column?: string;
      size_column?: string;
      z_column?: string;
      title: string;
    };
  }>;

  const safeTitle = resolvedTitle.replace(/[^a-zA-Z0-9\u4e00-\u9fa5]/g, "_");
  const formatLabel = output_format === "png" ? "PNG" : "HTML";

  await onProgress?.(60, 100);

  let outputPath: string;
  if (output_format === "png") {
    const buffer = await renderDashboardPng(
      chartInputs,
      resolvedTitle,
      theme,
      font_family,
      themeOverrides,
      resolvedLayout
    );
    outputPath = await writeOutputFile(`dashboard_${safeTitle}_${Date.now()}.png`, buffer);
  } else {
    const html = renderDashboardHtml(
      chartInputs,
      resolvedTitle,
      theme,
      font_family,
      themeOverrides,
      resolvedLayout
    );
    outputPath = await writeOutputFile(`dashboard_${safeTitle}_${Date.now()}.html`, html);
  }

  await onProgress?.(100, 100);
  const summary =
    resolvedLanguage === "zh"
      ? `已生成 ${formatLabel} 数据大屏：${resolvedTitle}\n包含 ${design.charts.length} 个图表\n布局：${resolvedLayout}\n文件路径：${outputPath}`
      : `Generated ${formatLabel} dashboard: ${resolvedTitle}\nContains ${design.charts.length} charts\nLayout: ${resolvedLayout}\nFile path: ${outputPath}`;

  return { content: [{ type: "text", text: summary }] };
}
