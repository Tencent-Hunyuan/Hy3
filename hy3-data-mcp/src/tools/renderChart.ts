import { z } from "zod";
import { renderChartHtml, renderChartSvg, type ChartType } from "../viz/echarts.js";
import { svgToPng } from "../viz/png.js";
import { loadInputData, resolveLanguage, resolveOutputFilename, writeOutputFile } from "../utils.js";
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
  "violin",
  "errorbar",
];

export const renderChartDefinition = {
  name: "hy3_render_chart",
  description:
    "Render a chart directly from explicit data + config. Does NOT call LLM. Required: chart_type, x_column, y_column (depending on chart_type). Output can be SVG, HTML, or PNG.",
  inputSchema: {
    type: "object" as const,
    properties: {
      data: { type: "string", description: "Inline structured data as a JSON array string." },
      data_file_path: { type: "string", description: "Path to a CSV/JSON/XLSX file." },
      file_path: { type: "string", description: "Alias for data_file_path." },
      chart_type: {
        type: "string",
        enum: SUPPORTED_CHART_TYPES,
        description: "Chart type.",
      },
      x_column: { type: "string", description: "Column for X axis or categories." },
      y_column: { type: "string", description: "Column for Y axis or values." },
      value_column: { type: "string", description: "Optional value/weight column (sankey, treemap, composite charts)." },
      open_column: { type: "string", description: "Optional candlestick open column." },
      close_column: { type: "string", description: "Optional candlestick close column." },
      high_column: { type: "string", description: "Optional candlestick high column." },
      low_column: { type: "string", description: "Optional candlestick low column." },
      group_column: { type: "string", description: "Optional grouping/stacking column." },
      size_column: { type: "string", description: "Optional bubble size column." },
      z_column: { type: "string", description: "Optional third dimension for 3D charts." },
      lower_column: { type: "string", description: "Optional lower bound column for errorbar charts." },
      upper_column: { type: "string", description: "Optional upper bound column for errorbar charts." },
      title: { type: "string", description: "Chart title." },
      subtitle: { type: "string", description: "Chart subtitle." },
      output_format: { type: "string", enum: ["svg", "html", "png"], default: "svg" },
      output_filename: { type: "string", description: "Optional custom output file name (without extension)." },
      width: { type: "number", description: "Chart width.", default: 800 },
      height: { type: "number", description: "Chart height.", default: 500 },
      theme: { type: "string", enum: ["light", "dark", "colorful", "minimal", "professional", "premium", "retro", "science", "nature"], default: "nature" },
      font_family: { type: "string" },
      background_color: { type: "string" },
      text_color: { type: "string" },
      axis_color: { type: "string" },
      split_line_color: { type: "string" },
      palette: { type: "array", items: { type: "string" } },
      primary_color: { type: "string" },
      legend_position: { type: "string", enum: ["top", "bottom", "left", "right"] },
      show_grid: { type: "boolean" },
      show_tooltip: { type: "boolean" },
      x_name: { type: "string" },
      y_name: { type: "string" },
      x_label_rotate: { type: "number" },
      line_smooth: { type: "boolean" },
      line_symbol: { type: "string", enum: ["circle", "rect", "triangle", "diamond", "pin", "arrow", "none"] },
      line_area: { type: "boolean" },
      bar_stack: { type: "boolean" },
      mark_point: { type: "boolean" },
      mark_line: { type: "boolean" },
      data_zoom: { type: "boolean" },
      overrides: { type: "string", description: "JSON string merged into the generated ECharts option." },
      show_data_table: { type: "boolean", description: "Whether to append the source data table below the chart (HTML only).", default: false },
      enable_theme_switcher: { type: "boolean", description: "Whether to add a theme switcher dropdown to the HTML output.", default: false },
      interactive_3d: { type: "boolean", description: "For 3D chart types, render an interactive WebGL scene (HTML output only).", default: false },
      language: { type: "string", enum: ["zh", "en", "auto"], default: "auto" },
    },
    required: ["chart_type", "x_column", "y_column"],
  },
};

export const renderChartSchema = z.object({
  data: z.string().optional(),
  data_file_path: z.string().optional(),
  file_path: z.string().optional(),
  chart_type: z.enum(SUPPORTED_CHART_TYPES as [string, ...string[]]),
  x_column: z.string().min(1),
  y_column: z.string().min(1),
  value_column: z.string().optional(),
  open_column: z.string().optional(),
  close_column: z.string().optional(),
  high_column: z.string().optional(),
  low_column: z.string().optional(),
  group_column: z.string().optional(),
  size_column: z.string().optional(),
  z_column: z.string().optional(),
  lower_column: z.string().optional(),
  upper_column: z.string().optional(),
  title: z.string().optional(),
  subtitle: z.string().optional(),
  output_format: z.enum(["svg", "html", "png"]).default("svg"),
  output_filename: z.string().optional(),
  width: z.number().int().min(200).max(2000).default(800),
  height: z.number().int().min(200).max(2000).default(500),
  theme: z.enum(["light", "dark", "colorful", "minimal", "professional", "premium", "retro", "science", "nature"]).default("nature"),
  font_family: z.string().optional(),
  background_color: z.string().optional(),
  text_color: z.string().optional(),
  axis_color: z.string().optional(),
  split_line_color: z.string().optional(),
  palette: z.array(z.string()).optional(),
  primary_color: z.string().optional(),
  legend_position: z.enum(["top", "bottom", "left", "right"]).optional(),
  show_grid: z.boolean().optional(),
  show_tooltip: z.boolean().optional(),
  x_name: z.string().optional(),
  y_name: z.string().optional(),
  x_label_rotate: z.number().optional(),
  line_smooth: z.boolean().optional(),
  line_symbol: z.enum(["circle", "rect", "triangle", "diamond", "pin", "arrow", "none"]).optional(),
  line_area: z.boolean().optional(),
  bar_stack: z.boolean().optional(),
  mark_point: z.boolean().optional(),
  mark_line: z.boolean().optional(),
  data_zoom: z.boolean().optional(),
  overrides: z.string().optional(),
  show_data_table: z.boolean().optional(),
  enable_theme_switcher: z.boolean().optional(),
  interactive_3d: z.boolean().optional(),
  language: z.enum(["zh", "en", "auto"]).default("auto"),
});

function validateChartColumns(
  chartType: ChartType,
  columns: string[],
  args: z.infer<typeof renderChartSchema>
) {
  const has = (col?: string) => col && columns.includes(col);
  const required: string[] = [];

  switch (chartType) {
    case "candlestick":
      if (!has(args.open_column)) required.push("open_column");
      if (!has(args.close_column)) required.push("close_column");
      if (!has(args.high_column)) required.push("high_column");
      if (!has(args.low_column)) required.push("low_column");
      break;
    case "bubble":
      if (!has(args.size_column)) required.push("size_column");
      break;
    case "sankey":
    case "treemap":
    case "sunburst":
      if (!has(args.value_column)) required.push("value_column");
      break;
    case "line_bar":
    case "area_bar":
    case "dual_axis":
      if (!has(args.value_column)) required.push("value_column");
      break;
    case "stacked_bar":
    case "grouped_bar":
    case "stacked_area":
    case "grouped_line":
      if (!has(args.group_column)) required.push("group_column");
      break;
    case "scatter3d":
    case "line3d":
      if (!has(args.z_column)) required.push("z_column");
      break;
    case "errorbar":
      if (!has(args.lower_column)) required.push("lower_column");
      if (!has(args.upper_column)) required.push("upper_column");
      break;
    default:
      break;
  }

  if (required.length > 0) {
    throw new Error(
      `Chart type '${chartType}' requires additional columns missing from the data: ${required.join(", ")}`
    );
  }
}

export async function runRenderChart(
  args: unknown,
  onProgress?: ProgressReporter
): Promise<{ content: Array<{ type: "text"; text: string }> }> {
  const {
    data,
    data_file_path,
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
    z_column,
    lower_column,
    upper_column,
    title,
    subtitle,
    output_format,
    width,
    height,
    theme,
    font_family,
    background_color,
    text_color,
    axis_color,
    split_line_color,
    palette,
    primary_color,
    legend_position,
    show_grid,
    show_tooltip,
    x_name,
    y_name,
    x_label_rotate,
    line_smooth,
    line_symbol,
    line_area,
    bar_stack,
    mark_point,
    mark_line,
    data_zoom,
    overrides,
    show_data_table,
    enable_theme_switcher,
    interactive_3d,
    output_filename,
    language,
  } = renderChartSchema.parse(args);

  if (!data && !data_file_path && !file_path) {
    throw new Error("One of data, data_file_path, or file_path is required");
  }

  await onProgress?.(10, 100);
  const table = await loadInputData({ data, data_file_path, file_path });
  await onProgress?.(30, 100);

  if (table.columns.length === 0) {
    throw new Error("No columns found in the data.");
  }

  if (!table.columns.includes(x_column)) {
    throw new Error(`x_column '${x_column}' not found in data. Available columns: ${table.columns.join(", ")}`);
  }
  if (!table.columns.includes(y_column)) {
    throw new Error(`y_column '${y_column}' not found in data. Available columns: ${table.columns.join(", ")}`);
  }

  const effectiveValueColumn =
    value_column || (["sunburst", "treemap"].includes(chart_type) ? y_column : undefined);

  validateChartColumns(chart_type as ChartType, table.columns, {
    value_column: effectiveValueColumn,
    open_column,
    close_column,
    high_column,
    low_column,
    group_column,
    size_column,
    z_column,
    lower_column,
    upper_column,
  } as z.infer<typeof renderChartSchema>);

  await onProgress?.(50, 100);

  const resolvedLanguage = resolveLanguage(language, title, table.raw);

  const config = {
    x_column,
    y_column,
    value_column: effectiveValueColumn,
    open_column,
    close_column,
    high_column,
    low_column,
    group_column,
    size_column,
    z_column,
    lower_column,
    upper_column,
    title: title || (resolvedLanguage === "zh" ? "数据图表" : "Data Chart"),
    subtitle,
    theme,
    font_family,
    background_color,
    text_color,
    axis_color,
    split_line_color,
    palette,
    primary_color,
    legend_position,
    show_grid,
    show_tooltip,
    x_name,
    y_name,
    x_label_rotate,
    line_smooth,
    line_symbol,
    line_area,
    bar_stack,
    mark_point,
    mark_line,
    data_zoom,
    overrides,
    show_data_table,
    enable_theme_switcher,
    interactive_3d,
    width,
    height,
  };

  let content: string | Buffer;
  let ext: string;

  if (output_format === "html") {
    content = renderChartHtml(chart_type as ChartType, table, config);
    ext = "html";
  } else if (output_format === "png") {
    const svg = renderChartSvg(chart_type as ChartType, table, config);
    content = await svgToPng(svg, width, height);
    ext = "png";
  } else {
    content = renderChartSvg(chart_type as ChartType, table, config);
    ext = "svg";
  }

  await onProgress?.(80, 100);
  const safeTitle = config.title.replace(/[^a-zA-Z0-9\u4e00-\u9fa5]/g, "_");
  const defaultName = `${safeTitle}_${Date.now()}`;
  const outputPath = await writeOutputFile(
    resolveOutputFilename(output_filename, defaultName, ext),
    content
  );

  await onProgress?.(100, 100);
  const formatLabel = output_format === "html" ? "HTML" : output_format === "png" ? "PNG" : "SVG";
  const summary =
    resolvedLanguage === "zh"
      ? `已生成 ${chart_type} ${formatLabel} 图表：${config.title}\nX 轴：${config.x_column}\nY 轴：${config.y_column}\n文件路径：${outputPath}`
      : `Generated ${chart_type} ${formatLabel} chart: ${config.title}\nX-axis: ${config.x_column}\nY-axis: ${config.y_column}\nFile path: ${outputPath}`;

  return { content: [{ type: "text" as const, text: summary }] };
}
