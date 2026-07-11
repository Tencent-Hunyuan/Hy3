import { z } from "zod";
import { basename } from "node:path";

import { Hy3Client } from "../client.js";
import { askHy3Json } from "../llm-utils.js";
import {
  colorOverrideSchema,
  dimensionsSchema,
  languageSchema,
  outputFilenameSchema,
  rawColorOverrideProperties,
  rawDimensionsProperties,
  rawLanguageProperty,
  rawOutputFilenameProperty,
  rawThemeProperty,
  themeSchema,
} from "../schemas.js";
import {
  assertColumnsExist,
  buildThemeOverrides,
  DataTable,
  loadDataTable,
  parseInlineData,
  resolveLanguage,
  resolveOutputFilename,
  tableSummary,
  validateDataTable,
  writeOutputFile,
} from "../utils.js";
import { renderChartSvg } from "../viz/echarts.js";
import { svgToPng } from "../viz/png.js";
import { getTheme } from "../viz/themes.js";
import type { ChartType } from "../viz/echarts.js";
import type { ProgressReporter } from "./index.js";

export const analyzeReportDefinition = {
  name: "hy3_analyze_report",
  description:
    "Generate a complete data analysis report from structured data. Hy3 analyzes the data, plans charts, and writes an HTML or Markdown report with embedded visualizations.",
  inputSchema: {
    type: "object" as const,
    properties: {
      file_paths: {
        type: "array",
        items: { type: "string" },
        description: "Paths to one or more CSV, JSON or XLSX files.",
      },
      file_path: {
        type: "string",
        description: "Path to a single CSV, JSON or XLSX file.",
      },
      data_file_path: {
        type: "string",
        description: "Path to a single CSV, JSON or XLSX file.",
      },
      data: {
        type: "string",
        description: "Inline structured data as a JSON array string.",
      },
      question: {
        type: "string",
        description: "Focus of the report, e.g. 'Summarize sales performance' or 'Find growth drivers'.",
        default: "Generate a comprehensive data analysis report",
      },
      output_format: {
        type: "string",
        enum: ["html", "markdown"],
        description: "'html' = self-contained HTML report; 'markdown' = Markdown report with embedded charts.",
        default: "html",
      },
      max_charts: {
        type: "number",
        description: "Maximum number of charts to include in the report.",
        default: 4,
      },
      ...rawDimensionsProperties(800, 420),
      ...rawThemeProperty("professional", "Color theme for charts."),
      font_family: { type: "string", description: "Custom font family for charts and report." },
      ...rawColorOverrideProperties,
      ...rawLanguageProperty("Language of the report. 'auto' detects from the question or data."),
      output_filename: rawOutputFilenameProperty(),
    },
    required: [],
  },
};

export const analyzeReportSchema = z.object({
  file_paths: z.array(z.string().min(1)).optional(),
  file_path: z.string().min(1).optional(),
  data_file_path: z.string().min(1).optional(),
  data: z.string().optional(),
  question: z.string().default("Generate a comprehensive data analysis report"),
  output_format: z.enum(["html", "markdown"]).default("html"),
  max_charts: z.number().int().min(1).max(8).default(4),
  ...dimensionsSchema(800, 420),
  theme: themeSchema("professional"),
  font_family: z.string().optional(),
  ...colorOverrideSchema.shape,
  language: languageSchema,
  output_filename: outputFilenameSchema,
});

interface ReportPlan {
  title: string;
  overview: string;
  sections: Array<{
    heading: string;
    text: string;
    chart?: {
      file_path?: string;
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
    };
  }>;
  conclusions: string;
  _warning?: string;
}

const reportPlanOutputSchema = z.object({
  title: z.string().optional(),
  overview: z.string().optional(),
  sections: z.array(
    z.object({
      heading: z.string().optional(),
      text: z.string().optional(),
      chart: z
        .object({
          file_path: z.string().optional(),
          chart_type: z.string(),
          x_column: z.string().optional(),
          y_column: z.string().optional(),
          value_column: z.string().optional(),
          open_column: z.string().optional(),
          close_column: z.string().optional(),
          high_column: z.string().optional(),
          low_column: z.string().optional(),
          group_column: z.string().optional(),
          size_column: z.string().optional(),
          z_column: z.string().optional(),
          title: z.string().optional(),
        })
        .optional(),
    })
  ),
  conclusions: z.string().optional(),
});

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

function buildChartConfig(
  chart: NonNullable<ReportPlan["sections"][number]["chart"]>,
  baseConfig: {
    theme: string;
    font_family?: string;
    background_color?: string;
    text_color?: string;
    axis_color?: string;
    split_line_color?: string;
    palette?: string[];
    width: number;
    height: number;
  }
) {
  const cfg: Record<string, unknown> = {
    x_column: chart.x_column,
    y_column: chart.y_column,
    title: chart.title,
    width: baseConfig.width,
    height: baseConfig.height,
    theme: baseConfig.theme,
    font_family: baseConfig.font_family,
    background_color: baseConfig.background_color,
    text_color: baseConfig.text_color,
    axis_color: baseConfig.axis_color,
    split_line_color: baseConfig.split_line_color,
    palette: baseConfig.palette,
  };
  if (chart.value_column) cfg.value_column = chart.value_column;
  if (chart.open_column) cfg.open_column = chart.open_column;
  if (chart.close_column) cfg.close_column = chart.close_column;
  if (chart.high_column) cfg.high_column = chart.high_column;
  if (chart.low_column) cfg.low_column = chart.low_column;
  if (chart.group_column) cfg.group_column = chart.group_column;
  if (chart.size_column) cfg.size_column = chart.size_column;
  if (chart.z_column) cfg.z_column = chart.z_column;
  return cfg;
}

function validChartType(type: string): type is ChartType {
  return (SUPPORTED_CHART_TYPES as string[]).includes(type);
}

export async function runAnalyzeReport(
  args: unknown,
  client: Hy3Client,
  onProgress?: ProgressReporter,
  signal?: AbortSignal,
  onOutput?: (chunk: string) => void
) {
  const {
    file_paths,
    file_path,
    data_file_path,
    data,
    question,
    output_format,
    max_charts,
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
    language,
    output_filename,
  } = analyzeReportSchema.parse(args);

  const hasFilePaths = file_paths && file_paths.length > 0;
  const hasSinglePath = file_path || data_file_path;
  const hasData = data && data.trim().length > 0;

  if (!hasFilePaths && !hasSinglePath && !hasData) {
    throw new Error("One of file_paths, file_path, data_file_path, or data must be provided");
  }

  await onProgress?.(5, 100);

  const tables: DataTable[] = [];
  const inputPaths: string[] = [];
  if (data) {
    tables.push(parseInlineData(data));
    inputPaths.push("<inline-data>");
  }
  if (hasSinglePath) {
    const singlePath = file_path || data_file_path;
    tables.push(await loadDataTable(singlePath!));
    inputPaths.push(singlePath!);
  }
  for (const path of file_paths ?? []) {
    tables.push(await loadDataTable(path));
    inputPaths.push(path);
  }
  tables.forEach((t) => validateDataTable(t));
  const firstTable = tables[0];

  const themeOverrides = buildThemeOverrides(
    { background_color, text_color, axis_color, split_line_color, palette, primary_color },
    theme
  );
  const combinedRaw = tables.map((t) => t.raw).join("\n");
  const resolvedLanguage = resolveLanguage(language, question, combinedRaw);

  await onProgress?.(15, 100);

  const fileSummaries = tables
    .map((t, i) => `File ${i + 1} (${basename(inputPaths[i])}):\n${tableSummary(t)}`)
    .join("\n\n");

  const system =
    resolvedLanguage === "zh"
      ? `你是一位资深数据分析师。请基于提供的 ${inputPaths.length} 个数据文件生成一份数据分析报告计划。支持的可视化图表类型包括：${SUPPORTED_CHART_TYPES.join(
          ", "
        )}。请返回纯 JSON，格式如下：
{
  "title": "报告标题",
  "overview": "数据概览与分析背景",
  "sections": [
    {
      "heading": "小节标题",
      "text": "该部分的数据分析与解读",
      "chart": {
        "file_path": "可选：该图表使用的数据文件路径，缺省则使用第一个文件",
        "chart_type": "图表类型",
        "x_column": "列名",
        "y_column": "列名",
        "value_column": "可选",
        "group_column": "可选",
        "size_column": "可选",
        "z_column": "可选：3D 图表的第三维",
        "title": "图表标题"
      }
    }
  ],
  "conclusions": "总结与建议"
}
要求：最多 ${max_charts} 个图表；每个 chart 必须仅使用其对应数据文件中存在的列名；不要输出任何额外文字。`
      : `You are a senior data analyst. Based on the provided ${inputPaths.length} data file(s), create a data analysis report plan. Supported chart types: ${SUPPORTED_CHART_TYPES.join(
          ", "
        )}. Return pure JSON in this shape:
{
  "title": "Report title",
  "overview": "Data overview and context",
  "sections": [
    {
      "heading": "Section heading",
      "text": "Analysis and interpretation for this section",
      "chart": {
        "file_path": "optional: path of the data file this chart uses; defaults to the first file if omitted",
        "chart_type": "chart type",
        "x_column": "column name",
        "y_column": "column name",
        "value_column": "optional",
        "group_column": "optional",
        "size_column": "optional",
        "z_column": "optional: third dimension for 3D charts",
        "title": "Chart title"
      }
    }
  ],
  "conclusions": "Summary and recommendations"
}
Requirements: at most ${max_charts} charts; each chart must only use columns that exist in its corresponding data file; no extra text.`;

  const user =
    resolvedLanguage === "zh"
      ? `分析任务：${question}\n\n${fileSummaries}`
      : `Analysis task: ${question}\n\n${fileSummaries}`;

  let plan: ReportPlan;
  try {
    await onProgress?.(30, 100);
    const parsed = await askHy3Json(client, system, user, reportPlanOutputSchema, { signal, onToken: onOutput });
    plan = {
      title: parsed.data.title || (resolvedLanguage === "zh" ? "数据分析报告" : "Data Analysis Report"),
      overview: parsed.data.overview || "",
      sections: (parsed.data.sections || []).map((section) => ({
        heading: section.heading || (resolvedLanguage === "zh" ? "分析" : "Analysis"),
        text: section.text || "",
        chart: section.chart
          ? {
              file_path: section.chart.file_path,
              chart_type: section.chart.chart_type as ChartType,
              x_column: section.chart.x_column || firstTable.columns[0],
              y_column: section.chart.y_column || firstTable.columns[1] || firstTable.columns[0],
              value_column: section.chart.value_column,
              open_column: section.chart.open_column,
              close_column: section.chart.close_column,
              high_column: section.chart.high_column,
              low_column: section.chart.low_column,
              group_column: section.chart.group_column,
              size_column: section.chart.size_column,
              z_column: section.chart.z_column,
              title: section.chart.title || (resolvedLanguage === "zh" ? "数据图表" : "Data Chart"),
            }
          : undefined,
      })),
      conclusions: parsed.data.conclusions || "",
    };
  } catch {
    plan = {
      title: resolvedLanguage === "zh" ? "数据分析报告" : "Data Analysis Report",
      overview: "",
      sections: [
        {
          heading: resolvedLanguage === "zh" ? "概览" : "Overview",
          text: resolvedLanguage === "zh" ? "基于提供的数据生成的概览分析。" : "Overview analysis based on the provided data.",
          chart: {
            chart_type: "bar",
            x_column: firstTable.columns[0],
            y_column: firstTable.columns[1] || firstTable.columns[0],
            title: resolvedLanguage === "zh" ? "数据概览" : "Data Overview",
          },
        },
      ],
      conclusions: "",
      _warning: resolvedLanguage === "zh" ? "模型输出解析失败，已使用默认报告方案。" : "Model output could not be parsed; using default report plan.",
    };
  }

  await onProgress?.(45, 100);

  const chartBaseConfig = {
    theme,
    font_family,
    background_color,
    text_color,
    axis_color,
    split_line_color,
    palette,
    width,
    height,
  };

  const chartImages: { heading: string; base64: string; title: string }[] = [];
  const sectionsWithCharts: Array<{ heading: string; text: string; chartIndex?: number }> = [];

  for (const section of plan.sections || []) {
    if (section.chart && validChartType(section.chart.chart_type)) {
      try {
        const cfg = buildChartConfig(section.chart, chartBaseConfig);
        let chartTable = firstTable;
        if (section.chart.file_path) {
          const idx = inputPaths.findIndex((p) => p === section.chart!.file_path);
          if (idx >= 0) chartTable = tables[idx];
        }
        assertColumnsExist(
          chartTable,
          [section.chart.x_column, section.chart.y_column, section.chart.value_column, section.chart.group_column, section.chart.size_column, section.chart.z_column],
          `Report chart '${section.chart.title}'`
        );
        const svg = renderChartSvg(section.chart.chart_type, chartTable, cfg as any);
        const png = await svgToPng(svg, width, height);
        const base64 = Buffer.from(png).toString("base64");
        chartImages.push({ heading: section.heading, title: section.chart.title, base64 });
        sectionsWithCharts.push({ heading: section.heading, text: section.text, chartIndex: chartImages.length - 1 });
      } catch {
        sectionsWithCharts.push({ heading: section.heading, text: section.text });
      }
    } else {
      sectionsWithCharts.push({ heading: section.heading, text: section.text });
    }
  }

  await onProgress?.(75, 100);

  const reportTheme = getTheme(theme, font_family, themeOverrides);
  const timestamp = Date.now();
  const fileExt = output_format === "markdown" ? "md" : "html";
  const defaultName = `data_report_${timestamp}`;
  const fileName = resolveOutputFilename(output_filename, defaultName, fileExt);

  const sourcePath = inputPaths.join(", ");
  let content: string;
  if (output_format === "markdown") {
    content = buildMarkdownReport(plan, sectionsWithCharts, chartImages, sourcePath, reportTheme);
  } else {
    content = buildHtmlReport(plan, sectionsWithCharts, chartImages, sourcePath, reportTheme);
  }

  const outputPath = await writeOutputFile(fileName, content);

  await onProgress?.(100, 100);

  const formatLabel = output_format === "markdown" ? "Markdown" : "HTML";
  const summary =
    resolvedLanguage === "zh"
      ? `已生成 ${formatLabel} 数据分析报告：${plan.title || "数据分析报告"}\n包含 ${chartImages.length} 张图表\n文件路径：${outputPath}`
      : `Generated ${formatLabel} data analysis report: ${plan.title || "Data Analysis Report"}\nIncludes ${chartImages.length} chart(s)\nFile path: ${outputPath}`;

  return { content: [{ type: "text" as const, text: summary }] };
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function buildHtmlReport(
  plan: ReportPlan,
  sections: Array<{ heading: string; text: string; chartIndex?: number }>,
  chartImages: { heading: string; base64: string; title: string }[],
  sourcePath: string,
  theme: ReturnType<typeof getTheme>
): string {
  const sectionHtml = sections
    .map((section) => {
      const chart =
        section.chartIndex !== undefined
          ? `<img src="data:image/png;base64,${chartImages[section.chartIndex].base64}" alt="${escapeHtml(
              chartImages[section.chartIndex].title
            )}" style="max-width:100%;height:auto;border-radius:8px;margin-top:12px;" />`
          : "";
      return `<section style="margin-bottom:32px;">
  <h2 style="font-size:20px;margin-bottom:10px;color:${theme.textColor};">${escapeHtml(section.heading)}</h2>
  <p style="line-height:1.7;color:${theme.textColor};">${escapeHtml(section.text)}</p>
  ${chart}
</section>`;
    })
    .join("\n");

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${escapeHtml(plan.title)}</title>
  <style>
    body { font-family: ${theme.fontFamily}; margin: 0; padding: 32px; background: ${theme.backgroundColor}; color: ${theme.textColor}; line-height: 1.7; font-size: 16px; font-weight: 400; }
    .container { max-width: 900px; margin: 0 auto; background: ${theme.backgroundColor}; }
    h1 { font-size: 28px; margin-bottom: 8px; font-weight: 600; }
    h2 { font-weight: 600; }
    .meta { color: ${theme.axisColor}; font-size: 14px; margin-bottom: 24px; }
    .overview, .conclusions { background: rgba(0,0,0,0.03); border-radius: 8px; padding: 16px; margin-bottom: 24px; }
    p, li { font-size: 16px; }
  </style>
</head>
<body>
  <div class="container">
    <h1>${escapeHtml(plan.title)}</h1>
    <div class="meta">Source: ${escapeHtml(sourcePath)}</div>
    <div class="overview">
      <h2 style="font-size:18px;margin-top:0;">Overview</h2>
      <p>${escapeHtml(plan.overview)}</p>
    </div>
    ${sectionHtml}
    <div class="conclusions">
      <h2 style="font-size:18px;margin-top:0;">Conclusions</h2>
      <p>${escapeHtml(plan.conclusions)}</p>
    </div>
  </div>
</body>
</html>`;
}

function buildMarkdownReport(
  plan: ReportPlan,
  sections: Array<{ heading: string; text: string; chartIndex?: number }>,
  chartImages: { heading: string; base64: string; title: string }[],
  sourcePath: string,
  _theme: ReturnType<typeof getTheme>
): string {
  const sectionMd = sections
    .map((section) => {
      const chart =
        section.chartIndex !== undefined
          ? `\n![${chartImages[section.chartIndex].title}](data:image/png;base64,${chartImages[section.chartIndex].base64})\n`
          : "";
      return `## ${section.heading}\n\n${section.text}${chart}`;
    })
    .join("\n\n");

  return `# ${plan.title}\n\n**Source:** ${sourcePath}\n\n## Overview\n\n${plan.overview}\n\n${sectionMd}\n\n## Conclusions\n\n${plan.conclusions}\n`;
}
