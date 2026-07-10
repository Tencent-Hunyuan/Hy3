import { z } from "zod";
import { renderKnowledgeGraphHtml, renderKnowledgeGraphSvg } from "../viz/echarts.js";
import { svgToPng } from "../viz/png.js";
import { buildThemeOverrides, writeOutputFile } from "../utils.js";
import type { ProgressReporter } from "./index.js";

export const renderKnowledgeGraphDefinition = {
  name: "hy3_render_knowledge_graph",
  description:
    "Render a knowledge graph directly from explicit nodes and links. Does NOT call LLM. Output can be SVG, HTML, or PNG.",
  inputSchema: {
    type: "object" as const,
    properties: {
      nodes: {
        type: "string",
        description: "JSON array string of {id, group} objects.",
      },
      links: {
        type: "string",
        description: "JSON array string of {source, target, relation} objects.",
      },
      title: { type: "string", default: "Knowledge Graph" },
      output_format: { type: "string", enum: ["svg", "html", "png"], default: "svg" },
      width: { type: "number", default: 900 },
      height: { type: "number", default: 600 },
      theme: { type: "string", enum: ["light", "dark", "colorful", "minimal", "professional", "premium", "retro", "science", "nature"], default: "nature" },
      font_family: { type: "string" },
      background_color: { type: "string" },
      text_color: { type: "string" },
      axis_color: { type: "string" },
      split_line_color: { type: "string" },
      palette: { type: "array", items: { type: "string" } },
      primary_color: { type: "string" },
    },
    required: ["nodes", "links"],
  },
};

export const renderKnowledgeGraphSchema = z.object({
  nodes: z.string().min(1),
  links: z.string().min(1),
  title: z.string().default("Knowledge Graph"),
  output_format: z.enum(["svg", "html", "png"]).default("svg"),
  width: z.number().int().min(200).max(2000).default(900),
  height: z.number().int().min(200).max(2000).default(600),
  theme: z.enum(["light", "dark", "colorful", "minimal", "professional", "premium", "retro", "science", "nature"]).default("nature"),
  font_family: z.string().optional(),
  background_color: z.string().optional(),
  text_color: z.string().optional(),
  axis_color: z.string().optional(),
  split_line_color: z.string().optional(),
  palette: z.array(z.string()).optional(),
  primary_color: z.string().optional(),
});

export async function runRenderKnowledgeGraph(
  args: unknown,
  onProgress?: ProgressReporter
): Promise<{ content: Array<{ type: "text"; text: string }> }> {
  const {
    nodes: nodesRaw,
    links: linksRaw,
    title,
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
  } = renderKnowledgeGraphSchema.parse(args);

  await onProgress?.(20, 100);

  const themeOverrides = buildThemeOverrides(
    { background_color, text_color, axis_color, split_line_color, palette, primary_color },
    theme
  );

  const nodes: { id: string; group: number }[] = JSON.parse(nodesRaw);
  let links: { source: string; target: string; relation: string }[] = JSON.parse(linksRaw);

  const nodeIds = new Set(nodes.map((n) => n.id));
  links = links.filter((l) => nodeIds.has(l.source) && nodeIds.has(l.target));

  if (nodes.length === 0) {
    throw new Error("At least one node is required");
  }

  await onProgress?.(60, 100);
  let content: string | Buffer;
  let fileExt: string;

  if (output_format === "html") {
    content = renderKnowledgeGraphHtml(nodes, links, title, width, height, theme, font_family, themeOverrides);
    fileExt = "html";
  } else if (output_format === "png") {
    const svg = renderKnowledgeGraphSvg(nodes, links, title, width, height, theme, font_family, themeOverrides);
    content = await svgToPng(svg, width, height);
    fileExt = "png";
  } else {
    content = renderKnowledgeGraphSvg(nodes, links, title, width, height, theme, font_family, themeOverrides);
    fileExt = "svg";
  }

  const outputPath = await writeOutputFile(`knowledge_graph_${Date.now()}.${fileExt}`, content);

  await onProgress?.(100, 100);
  const formatLabel = output_format === "html" ? "HTML" : output_format === "png" ? "PNG" : "SVG";
  const summary = `Generated ${formatLabel} knowledge graph: ${nodes.length} entities, ${links.length} relationships\nFile path: ${outputPath}`;

  return { content: [{ type: "text" as const, text: summary }] };
}
