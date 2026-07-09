import { z } from "zod";
import { extname } from "path";
import { Hy3Client } from "../client.js";
import { renderKnowledgeGraphHtml, renderKnowledgeGraphSvg } from "../viz/echarts.js";
import { svgToPng } from "../viz/png.js";
import {
  askHy3,
  buildThemeOverrides,
  loadDataTable,
  sampleText,
  writeOutputFile,
} from "../utils.js";

export const knowledgeGraphDefinition = {
  name: "hy3_knowledge_graph",
  description:
    "Extract a knowledge graph (entities and relationships) from a text, CSV, JSON or XLSX file using Hy3, and render it as an SVG or animated HTML force-directed graph via ECharts.",
  inputSchema: {
    type: "object" as const,
    properties: {
      file_path: {
        type: "string",
        description: "Path to a text, CSV, JSON or XLSX file.",
      },
      column: {
        type: "string",
        description:
          "For CSV/JSON/XLSX, the text column to analyze. Leave empty to let Hy3 choose.",
      },
      max_entities: {
        type: "number",
        description: "Maximum number of entities to display.",
        default: 30,
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
        description: "Width in pixels.",
        default: 900,
      },
      height: {
        type: "number",
        description: "Height in pixels.",
        default: 600,
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
        description: "Color theme of the graph.",
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
        description: "Language of the text.",
        default: "zh",
      },
    },
    required: ["file_path"],
  },
};

const knowledgeGraphSchema = z.object({
  file_path: z.string().min(1),
  column: z.string().optional(),
  max_entities: z.number().int().min(5).max(100).default(30),
  output_format: z.enum(["svg", "html", "png"]).default("svg"),
  width: z.number().int().min(200).max(2000).default(900),
  height: z.number().int().min(200).max(2000).default(600),
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

export async function runKnowledgeGraph(args: unknown, client: Hy3Client) {
  const {
    file_path,
    column,
    max_entities,
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
    language,
  } = knowledgeGraphSchema.parse(args);

  const themeOverrides = buildThemeOverrides(
    { background_color, text_color, axis_color, split_line_color, palette, primary_color },
    theme
  );
  const ext = extname(file_path);

  let text: string;
  if (ext === ".csv" || ext === ".json" || ext === ".jsonl" || ext === ".xlsx" || ext === ".xls") {
    const table = await loadDataTable(file_path);
    const targetColumn =
      column ||
      table.columns.find((c) =>
        /text|content|comment|review|description|描述|内容|评论/i.test(c)
      ) ||
      table.columns[0];
    text = table.rows.map((row) => String(row[targetColumn] ?? "")).join("\n");
  } else {
    const raw = await loadDataTable(file_path);
    text = raw.raw;
  }

  const system =
    language === "zh"
      ? `你是一位知识图谱专家。请从以下文本中提取实体和关系。以纯 JSON 返回：{"nodes": [{"id": "实体名", "group": 1}, ...], "links": [{"source": "实体A", "target": "实体B", "relation": "关系"}, ...]}。实体最多 ${max_entities} 个。不要输出任何额外文字。`
      : `You are a knowledge-graph expert. Extract entities and relationships from the text below. Return pure JSON: {"nodes": [{"id": "entity name", "group": 1}, ...], "links": [{"source": "entity A", "target": "entity B", "relation": "relationship"}, ...]}. At most ${max_entities} entities. No extra text.`;

  let graph: {
    nodes: { id: string; group: number }[];
    links: { source: string; target: string; relation: string }[];
  };
  try {
    const answer = await askHy3(client, system, sampleText(text));
    graph = JSON.parse(answer);
  } catch {
    graph = { nodes: [], links: [] };
  }

  if (graph.nodes.length === 0) {
    return {
      content: [
        {
          type: "text" as const,
          text:
            language === "zh"
              ? "未能从文本中抽取到知识图谱。"
              : "No knowledge graph could be extracted from the text.",
        },
      ],
    };
  }

  const nodeIds = new Set(graph.nodes.map((n) => n.id));
  const links = graph.links.filter((l) => nodeIds.has(l.source) && nodeIds.has(l.target));

  const title = language === "zh" ? "知识图谱" : "Knowledge Graph";
  let content: string | Buffer;
  let fileExt: string;

  if (output_format === "html") {
    content = renderKnowledgeGraphHtml(
      graph.nodes,
      links,
      title,
      width,
      height,
      theme,
      font_family,
      themeOverrides
    );
    fileExt = "html";
  } else if (output_format === "png") {
    const svg = renderKnowledgeGraphSvg(
      graph.nodes,
      links,
      title,
      width,
      height,
      theme,
      font_family,
      themeOverrides
    );
    content = await svgToPng(svg, width, height);
    fileExt = "png";
  } else {
    content = renderKnowledgeGraphSvg(
      graph.nodes,
      links,
      title,
      width,
      height,
      theme,
      font_family,
      themeOverrides
    );
    fileExt = "svg";
  }

  const outputPath = await writeOutputFile(`knowledge_graph_${Date.now()}.${fileExt}`, content);

  const formatLabel = output_format === "html" ? "HTML" : output_format === "png" ? "PNG" : "SVG";
  const summary =
    language === "zh"
      ? `已生成 ${formatLabel} 知识图谱：${graph.nodes.length} 个实体，${links.length} 条关系\n文件路径：${outputPath}`
      : `Generated ${formatLabel} knowledge graph: ${graph.nodes.length} entities, ${links.length} relationships\nFile path: ${outputPath}`;

  return { content: [{ type: "text" as const, text: summary }] };
}
