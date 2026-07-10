import { z } from "zod";
import { Hy3Client } from "../client.js";
import { renderChartHtml, renderChartSvg, type ChartType } from "../viz/echarts.js";
import { svgToPng } from "../viz/png.js";
import { askHy3, loadDataTable, resolveLanguage, tableSummary, writeOutputFile } from "../utils.js";
import type { ProgressReporter } from "./index.js";

export const dataVisualizeDefinition = {
  name: "hy3_data_visualize",
  description:
    "Generate a professional chart (bar, line, area, pie, donut, rose, scatter, bubble, scatter_trend, radar, heatmap, funnel, sankey, treemap, sunburst, gauge, histogram, boxplot, candlestick, stacked_bar, grouped_bar) from a CSV/JSON/XLSX file using Hy3 to choose columns. Output can be a static SVG, an animated/interactive HTML page, or a PNG image powered by ECharts.",
  inputSchema: {
    type: "object" as const,
    properties: {
      file_path: {
        type: "string",
        description: "Path to a CSV, JSON or XLSX file.",
      },
      chart_type: {
        type: "string",
        enum: [
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
        ],
        description: "Desired chart type.",
        default: "bar",
      },
      x_column: {
        type: "string",
        description: "Column to use for the X axis or categories. Leave empty to let Hy3 choose.",
      },
      y_column: {
        type: "string",
        description: "Column to use for the Y axis or values. Leave empty to let Hy3 choose.",
      },
      value_column: {
        type: "string",
        description:
          "Optional column for weight/value (used by sankey, treemap, etc.). Leave empty to let Hy3 choose.",
      },
      open_column: {
        type: "string",
        description: "Optional column for candlestick open price. Leave empty to let Hy3 choose.",
      },
      close_column: {
        type: "string",
        description: "Optional column for candlestick close price. Leave empty to let Hy3 choose.",
      },
      high_column: {
        type: "string",
        description: "Optional column for candlestick high price. Leave empty to let Hy3 choose.",
      },
      low_column: {
        type: "string",
        description: "Optional column for candlestick low price. Leave empty to let Hy3 choose.",
      },
      group_column: {
        type: "string",
        description:
          "Optional column for grouping/stacking series (used by stacked_bar, grouped_bar). Leave empty to let Hy3 choose.",
      },
      size_column: {
        type: "string",
        description:
          "Optional column for bubble size (used by bubble). Leave empty to let Hy3 choose.",
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
        description: "Color theme of the chart.",
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
      title: {
        type: "string",
        description: "Chart title. Leave empty to let Hy3 generate one.",
      },
      output_format: {
        type: "string",
        enum: ["svg", "html", "png"],
        description:
          "'svg' = static SVG; 'html' = animated/interactive ECharts page; 'png' = PNG image.",
        default: "svg",
      },
      width: {
        type: "number",
        description: "Chart width in pixels.",
        default: 800,
      },
      height: {
        type: "number",
        description: "Chart height in pixels.",
        default: 500,
      },
      language: {
        type: "string",
        enum: ["zh", "en", "auto"],
        description: "Language of the chart title and labels. 'auto' detects from title or data.",
        default: "auto",
      },
    },
    required: ["file_path"],
  },
};

const dataVisualizeSchema = z.object({
  file_path: z.string().min(1),
  chart_type: z
    .enum([
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
    ])
    .default("bar"),
  x_column: z.string().optional(),
  y_column: z.string().optional(),
  value_column: z.string().optional(),
  open_column: z.string().optional(),
  close_column: z.string().optional(),
  high_column: z.string().optional(),
  low_column: z.string().optional(),
  group_column: z.string().optional(),
  size_column: z.string().optional(),
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
  title: z.string().optional(),
  output_format: z.enum(["svg", "html", "png"]).default("svg"),
  width: z.number().int().min(200).max(2000).default(800),
  height: z.number().int().min(200).max(2000).default(500),
  language: z.enum(["zh", "en", "auto"]).default("auto"),
});

export async function runDataVisualize(
  args: unknown,
  client: Hy3Client,
  onProgress?: ProgressReporter
) {
  const {
    file_path,
    chart_type,
    x_column,
    y_column,
    value_column,
    open_column,
    close_column,
    high_column,
    low_column,
    group_column,
    size_column,
    theme,
    font_family,
    background_color,
    text_color,
    axis_color,
    split_line_color,
    palette,
    primary_color,
    title,
    output_format,
    width,
    height,
    language,
  } = dataVisualizeSchema.parse(args);

  await onProgress?.(10, 100);
  const table = await loadDataTable(file_path);
  await onProgress?.(30, 100);

  if (table.columns.length === 0) {
    throw new Error("No columns found in the data file.");
  }

  const resolvedLanguage = resolveLanguage(language, title, table.raw);

  const system =
    resolvedLanguage === "zh"
      ? '你是一位数据可视化专家。请根据图表类型推荐合适的列，并以纯 JSON 返回：{"x_column": string, "y_column": string, "value_column": string?, "open_column": string?, "close_column": string?, "high_column": string?, "low_column": string?, "group_column": string?, "size_column": string?, "title": string}。说明：普通图表使用 x_column/y_column；桑基图使用 x_column 作为 source、y_column 作为 target、value_column 作为流量；矩形树图/旭日图使用 x_column 作为名称、y_column 作为数值；K 线图使用 open_column/close_column/low_column/high_column；堆叠/分组柱状图使用 group_column；气泡图使用 size_column 控制点大小；直方图自动对数值列分箱。不要输出任何额外文字。'
      : 'You are a data visualization expert. Recommend suitable columns for the requested chart type and return only pure JSON: {"x_column": string, "y_column": string, "value_column": string?, "open_column": string?, "close_column": string?, "high_column": string?, "low_column": string?, "group_column": string?, "size_column": string?, "title": string}. Notes: regular charts use x_column/y_column; sankey uses x_column as source, y_column as target, value_column as weight; treemap/sunburst use x_column as name and y_column as value; candlestick uses open_column/close_column/low_column/high_column; stacked/grouped bar uses group_column; bubble uses size_column for point size; histogram auto-bins a numeric column. No extra text.';

  const user =
    resolvedLanguage === "zh"
      ? `用户想要的图表类型：${chart_type}\n数据摘要：\n${tableSummary(table)}\n用户指定的 x_column: ${x_column || "（未指定）"}, y_column: ${y_column || "（未指定）"}, value_column: ${value_column || "（未指定）"}, group_column: ${group_column || "（未指定）"}, size_column: ${size_column || "（未指定）"}, title: ${title || "（未指定）"}`
      : `Requested chart type: ${chart_type}\nData summary:\n${tableSummary(table)}\nUser specified x_column: ${x_column || "(none)"}, y_column: ${y_column || "(none)"}, value_column: ${value_column || "(none)"}, group_column: ${group_column || "(none)"}, size_column: ${size_column || "(none)"}, title: ${title || "(none)"}`;

  let config: {
    x_column: string;
    y_column: string;
    value_column?: string;
    open_column?: string;
    close_column?: string;
    high_column?: string;
    low_column?: string;
    group_column?: string;
    size_column?: string;
    title: string;
  };
  try {
    await onProgress?.(50, 100);
    const answer = await askHy3(client, system, user);
    config = JSON.parse(answer);
    await onProgress?.(80, 100);
  } catch {
    config = {
      x_column: x_column || table.columns[0],
      y_column: y_column || table.columns[1] || table.columns[0],
      title: title || (resolvedLanguage === "zh" ? "数据可视化" : "Data Visualization"),
    };
  }

  if (x_column) config.x_column = x_column;
  if (y_column) config.y_column = y_column;
  if (value_column) config.value_column = value_column;
  if (open_column) config.open_column = open_column;
  if (close_column) config.close_column = close_column;
  if (high_column) config.high_column = high_column;
  if (low_column) config.low_column = low_column;
  if (group_column) config.group_column = group_column;
  if (size_column) config.size_column = size_column;
  if (title) config.title = title;

  const chartConfig = {
    ...config,
    theme,
    font_family,
    background_color,
    text_color,
    axis_color,
    split_line_color,
    palette,
    primary_color,
    width,
    height,
  };
  let content: string | Buffer;
  let ext: string;

  if (output_format === "html") {
    content = renderChartHtml(chart_type as ChartType, table, chartConfig);
    ext = "html";
  } else if (output_format === "png") {
    const svg = renderChartSvg(chart_type as ChartType, table, chartConfig);
    content = await svgToPng(svg, width, height);
    ext = "png";
  } else {
    content = renderChartSvg(chart_type as ChartType, table, chartConfig);
    ext = "svg";
  }

  const safeTitle = config.title.replace(/[^a-zA-Z0-9\u4e00-\u9fa5]/g, "_");
  const outputPath = await writeOutputFile(`${safeTitle}_${Date.now()}.${ext}`, content);

  await onProgress?.(100, 100);
  const formatLabel = output_format === "html" ? "HTML" : output_format === "png" ? "PNG" : "SVG";
  const summary =
    resolvedLanguage === "zh"
      ? `已生成 ${chart_type} ${formatLabel} 图表：${config.title}\nX 轴：${config.x_column}\nY 轴：${config.y_column}\n文件路径：${outputPath}`
      : `Generated ${chart_type} ${formatLabel} chart: ${config.title}\nX-axis: ${config.x_column}\nY-axis: ${config.y_column}\nFile path: ${outputPath}`;

  return { content: [{ type: "text" as const, text: summary }] };
}
