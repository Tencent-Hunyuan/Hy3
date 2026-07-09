import { z } from "zod";
import { Hy3Client } from "../client.js";
import { extractTextFromDocument, detectDocumentType } from "../documents.js";
import { renderChartHtml, renderChartSvg, type ChartType } from "../viz/echarts.js";
import { svgToPng } from "../viz/png.js";
import {
  askHy3,
  buildThemeOverrides,
  loadDataTable,
  sampleText,
  tableSummary,
  writeOutputFile,
} from "../utils.js";

export const documentVisualizeDefinition = {
  name: "hy3_document_visualize",
  description:
    "Read a PDF, Word (DOCX), TXT or structured file (CSV/JSON/XLSX), use Hy3 to extract or summarize key data, and generate a chart or dashboard visualization.",
  inputSchema: {
    type: "object" as const,
    properties: {
      file_path: {
        type: "string",
        description: "Path to a PDF, DOCX, TXT, CSV, JSON or XLSX file.",
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
          "dashboard",
        ],
        description: "Chart type or 'dashboard' for a multi-chart dashboard.",
        default: "bar",
      },
      output_format: {
        type: "string",
        enum: ["svg", "html", "png"],
        description:
          "'svg' = static SVG; 'html' = animated/interactive ECharts page; 'png' = PNG image.",
        default: "html",
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

const documentVisualizeSchema = z.object({
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
      "dashboard",
    ])
    .default("bar"),
  output_format: z.enum(["svg", "html", "png"]).default("html"),
  width: z.number().int().min(200).max(2000).default(800),
  height: z.number().int().min(200).max(2000).default(500),
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
  language: z.enum(["zh", "en"]).default("zh"),
});

export async function runDocumentVisualize(args: unknown, client: Hy3Client) {
  const {
    file_path,
    chart_type,
    output_format,
    width,
    height,
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
    language,
  } = documentVisualizeSchema.parse(args);

  const themeOverrides = buildThemeOverrides(
    { background_color, text_color, axis_color, split_line_color, palette, primary_color },
    theme
  );

  const docType = detectDocumentType(file_path);
  let table;

  if (docType === "xlsx" || docType === "csv" || docType === "json") {
    table = await loadDataTable(file_path);
  } else {
    const text = await extractTextFromDocument(file_path);
    if (!text.trim()) {
      throw new Error("No text could be extracted from the document.");
    }

    const system =
      language === "zh"
        ? '你是一位数据提取专家。请从以下文档内容中提取结构化数据，并以纯 JSON 返回：{"columns": ["列1", "列2"], "rows": [{"列1": "值", "列2": 123}, ...]}。数字字段请尽量使用数字类型。不要输出任何额外文字。'
        : 'You are a data-extraction expert. Extract structured data from the document content below and return pure JSON: {"columns": ["col1", "col2"], "rows": [{"col1": "value", "col2": 123}, ...]}. Use numbers for numeric fields. No extra text.';

    try {
      const answer = await askHy3(client, system, sampleText(text, 20000));
      const parsed = JSON.parse(answer);
      table = {
        columns: parsed.columns,
        rows: parsed.rows,
        raw: JSON.stringify(parsed),
      };
    } catch {
      throw new Error(
        language === "zh"
          ? "无法从文档中提取结构化数据，请尝试使用 hy3_document_summary 进行总结。"
          : "Could not extract structured data from the document. Try hy3_document_summary instead."
      );
    }
  }

  if (table.columns.length === 0) {
    throw new Error("No columns found in the extracted data.");
  }

  const system =
    language === "zh"
      ? '你是一位数据可视化专家。请根据图表类型推荐合适的列，并以纯 JSON 返回：{"x_column": string, "y_column": string, "value_column": string?, "open_column": string?, "close_column": string?, "high_column": string?, "low_column": string?, "group_column": string?, "size_column": string?, "title": string}。说明：普通图表使用 x_column/y_column；桑基图使用 x_column 作为 source、y_column 作为 target、value_column 作为流量；矩形树图/旭日图使用 x_column 作为名称、y_column 作为数值；K 线图使用 open_column/close_column/low_column/high_column；堆叠/分组柱状图使用 group_column；气泡图使用 size_column 控制点大小；直方图自动对数值列分箱。不要输出任何额外文字。'
      : 'You are a data visualization expert. Recommend suitable columns for the requested chart type and return only pure JSON: {"x_column": string, "y_column": string, "value_column": string?, "open_column": string?, "close_column": string?, "high_column": string?, "low_column": string?, "group_column": string?, "size_column": string?, "title": string}. Notes: regular charts use x_column/y_column; sankey uses x_column as source, y_column as target, value_column as weight; treemap/sunburst use x_column as name and y_column as value; candlestick uses open_column/close_column/low_column/high_column; stacked/grouped bar uses group_column; bubble uses size_column for point size; histogram auto-bins a numeric column. No extra text.';

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
    const answer = await askHy3(client, system, tableSummary(table));
    config = JSON.parse(answer);
  } catch {
    config = {
      x_column: table.columns[0],
      y_column: table.columns[1] || table.columns[0],
      title: language === "zh" ? "文档可视化" : "Document Visualization",
    };
  }

  if (value_column) config.value_column = value_column;
  if (open_column) config.open_column = open_column;
  if (close_column) config.close_column = close_column;
  if (high_column) config.high_column = high_column;
  if (low_column) config.low_column = low_column;
  if (group_column) config.group_column = group_column;
  if (size_column) config.size_column = size_column;

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

  if (chart_type === "dashboard") {
    // For dashboard, reuse data dashboard logic: one chart from the extracted data
    const { renderDashboardHtml } = await import("../viz/echarts.js");
    const html = renderDashboardHtml(
      [
        {
          chartType: "bar" as ChartType,
          table,
          config: { x_column: config.x_column, y_column: config.y_column, title: config.title },
        },
      ],
      config.title,
      theme,
      font_family,
      themeOverrides
    );
    const outputPath = await writeOutputFile(`document_dashboard_${Date.now()}.html`, html);
    return {
      content: [
        {
          type: "text" as const,
          text:
            language === "zh"
              ? `已生成文档数据大屏\n文件路径：${outputPath}`
              : `Generated document dashboard\nFile path: ${outputPath}`,
        },
      ],
    };
  }

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
  const outputPath = await writeOutputFile(`document_${safeTitle}_${Date.now()}.${ext}`, content);

  const formatLabel = output_format === "html" ? "HTML" : output_format === "png" ? "PNG" : "SVG";
  const summary =
    language === "zh"
      ? `已生成 ${chart_type} ${formatLabel} 文档可视化：${config.title}\n文件路径：${outputPath}`
      : `Generated ${chart_type} ${formatLabel} document visualization: ${config.title}\nFile path: ${outputPath}`;

  return { content: [{ type: "text" as const, text: summary }] };
}
