import { z } from "zod";
import { Hy3Client } from "../client.js";
import { renderDashboardHtml, renderDashboardPng, type ChartType } from "../viz/echarts.js";
import {
  askHy3,
  buildThemeOverrides,
  DataTable,
  loadDataTable,
  resolveLanguage,
  tableSummary,
  writeOutputFile,
} from "../utils.js";
import type { ProgressReporter } from "./index.js";

export const dataDashboardDefinition = {
  name: "hy3_data_dashboard",
  description:
    "Generate a full interactive dashboard (HTML with inline SVG charts) from one or more CSV/JSON files. Hy3 designs the layout and chooses chart types; ECharts renders each chart as SVG.",
  inputSchema: {
    type: "object" as const,
    properties: {
      file_paths: {
        type: "array",
        items: { type: "string" },
        description: "List of CSV or JSON files to include in the dashboard.",
      },
      title: {
        type: "string",
        description: "Dashboard title. Leave empty to let Hy3 generate one.",
      },
      theme: {
        type: "string",
        enum: [
          "light",
          "dark",
          "colorful",
          "minimal",
          "professional",
          "retro",
          "science",
          "nature",
        ],
        description: "Dashboard color theme.",
        default: "light",
      },
      font_family: {
        type: "string",
        description:
          "Custom font family for titles and labels. Leave empty to use the theme default.",
      },
      background_color: {
        type: "string",
        description: "Optional custom background color hex (e.g. #ffffff). Overrides the theme.",
      },
      text_color: {
        type: "string",
        description: "Optional custom text/label color hex (e.g. #1a1a1a). Overrides the theme.",
      },
      axis_color: {
        type: "string",
        description:
          "Optional custom axis line/tick color hex (e.g. #999999). Overrides the theme.",
      },
      split_line_color: {
        type: "string",
        description:
          "Optional custom grid split line color hex (e.g. #e8e8e8). Overrides the theme.",
      },
      palette: {
        type: "array",
        items: { type: "string" },
        description:
          "Optional custom color palette as an array of hex colors. Overrides the theme palette.",
      },
      primary_color: {
        type: "string",
        description:
          "Optional primary color hex. When palette is not provided, replaces the first theme color.",
      },
      output_format: {
        type: "string",
        enum: ["html", "png"],
        description: "'html' = interactive dashboard page; 'png' = static composite image.",
        default: "html",
      },
      language: {
        type: "string",
        enum: ["zh", "en", "auto"],
        description: "Language of titles and labels. 'auto' detects from title/question or data.",
        default: "auto",
      },
      layout: {
        type: "string",
        enum: ["grid", "rows", "columns", "hero", "compact"],
        description: "Dashboard layout style.",
        default: "grid",
      },
    },
    required: ["file_paths"],
  },
};

export const dataDashboardSchema = z.object({
  file_paths: z.array(z.string().min(1)).min(1),
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
  output_format: z.enum(["html", "png"]).default("html"),
  language: z.enum(["zh", "en", "auto"]).default("auto"),
  layout: z.enum(["grid", "rows", "columns", "hero", "compact"]).default("grid"),
});

export async function runDataDashboard(
  args: unknown,
  client: Hy3Client,
  onProgress?: ProgressReporter,
  signal?: AbortSignal,
  _onOutput?: (chunk: string) => void
) {
  const {
    file_paths,
    title,
    theme,
    font_family,
    background_color,
    text_color,
    axis_color,
    split_line_color,
    palette,
    primary_color,
    output_format,
    language,
    layout,
  } = dataDashboardSchema.parse(args);

  await onProgress?.(10, 100);

  const themeOverrides = buildThemeOverrides(
    { background_color, text_color, axis_color, split_line_color, palette, primary_color },
    theme
  );

  const tables: { path: string; table: DataTable }[] = [];
  for (const path of file_paths) {
    tables.push({ path, table: await loadDataTable(path) });
  }
  await onProgress?.(25, 100);

  const resolvedLanguage = resolveLanguage(language, title);

  const summaryText = tables
    .map(({ path, table }) => `File: ${path}\n${tableSummary(table)}`)
    .join("\n\n");

  await onProgress?.(40, 100);

  const system =
    resolvedLanguage === "zh"
      ? '你是一位数据大屏设计专家。请基于提供的数据文件，设计一个可视化大屏布局。支持的图表类型：bar、line、area、pie、donut、rose、scatter、bubble、scatter_trend、radar、heatmap、funnel、sankey、treemap、sunburst、gauge、histogram、boxplot、stacked_bar、grouped_bar、bar3d、scatter3d、line3d、line_bar、area_bar、dual_axis、stacked_area、grouped_line。以纯 JSON 返回：{"title": string, "charts": [{"file_index": number, "chart_type": string, "x_column": string, "y_column": string, "value_column": string?, "group_column": string?, "size_column": string?, "z_column": string?, "title": string}] }。不要输出任何额外文字。'
      : 'You are a dashboard design expert. Based on the provided data files, design a visualization dashboard layout. Supported chart types: bar, line, area, pie, donut, rose, scatter, bubble, scatter_trend, radar, heatmap, funnel, sankey, treemap, sunburst, gauge, histogram, boxplot, stacked_bar, grouped_bar, bar3d, scatter3d, line3d, line_bar, area_bar, dual_axis, stacked_area, grouped_line. Return pure JSON: {"title": string, "charts": [{"file_index": number, "chart_type": string, "x_column": string, "y_column": string, "value_column": string?, "group_column": string?, "size_column": string?, "z_column": string?, "title": string}] }. No extra text.';

  let design: {
    title: string;
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
  try {
    await onProgress?.(55, 100);
    const answer = await askHy3(client, system, summaryText, signal, _onOutput);
    design = JSON.parse(answer);
  } catch {
    design = {
      title: title || (language === "zh" ? "数据大屏" : "Data Dashboard"),
      charts: tables.slice(0, 1).map(({ table }, i) => ({
        file_index: i,
        chart_type: "bar",
        x_column: table.columns[0],
        y_column: table.columns[1] || table.columns[0],
        title: language === "zh" ? "概览" : "Overview",
      })),
    };
  }

  if (title) design.title = title;
  await onProgress?.(70, 100);

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

  const safeTitle = design.title.replace(/[^a-zA-Z0-9\u4e00-\u9fa5]/g, "_");
  const formatLabel = output_format === "png" ? "PNG" : "HTML";

  await onProgress?.(80, 100);

  let outputPath: string;
  if (output_format === "png") {
    const buffer = await renderDashboardPng(
      chartInputs,
      design.title,
      theme,
      font_family,
      themeOverrides,
      layout
    );
    outputPath = await writeOutputFile(`dashboard_${safeTitle}_${Date.now()}.png`, buffer);
  } else {
    const html = renderDashboardHtml(chartInputs, design.title, theme, font_family, themeOverrides, layout);
    outputPath = await writeOutputFile(`dashboard_${safeTitle}_${Date.now()}.html`, html);
  }

  await onProgress?.(100, 100);
  const summary =
    resolvedLanguage === "zh"
      ? `已生成 ${formatLabel} 数据大屏：${design.title}\n包含 ${design.charts.length} 个图表\n布局：${layout}\n文件路径：${outputPath}`
      : `Generated ${formatLabel} dashboard: ${design.title}\nContains ${design.charts.length} charts\nLayout: ${layout}\nFile path: ${outputPath}`;

  return { content: [{ type: "text" as const, text: summary }] };
}
