import { z } from "zod";
import { renderKnowledgeGraphHtml, renderKnowledgeGraphSvg } from "../viz/echarts.js";
import { svgToPng } from "../viz/png.js";
import {
  colorOverrideSchema,
  dimensionsSchema,
  outputFilenameSchema,
  rawColorOverrideProperties,
  rawDimensionsProperties,
  rawOutputFilenameProperty,
  rawThemeProperty,
  themeSchema,
} from "../schemas.js";
import { safeJsonParse } from "../llm-utils.js";
import { buildThemeOverrides, resolveOutputFilename, writeOutputFile } from "../utils.js";
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
      output_filename: rawOutputFilenameProperty(),
      ...rawDimensionsProperties(900, 600),
      ...rawThemeProperty("nature"),
      font_family: { type: "string" },
      ...rawColorOverrideProperties,
    },
    required: ["nodes", "links"],
  },
};

const nodeSchema = z.object({ id: z.string().min(1), group: z.number().int().optional() });
const linkSchema = z.object({
  source: z.string().min(1),
  target: z.string().min(1),
  relation: z.string().optional(),
});

export const renderKnowledgeGraphSchema = z.object({
  nodes: z.string().min(1),
  links: z.string().min(1),
  title: z.string().default("Knowledge Graph"),
  output_format: z.enum(["svg", "html", "png"]).default("svg"),
  output_filename: outputFilenameSchema,
  ...dimensionsSchema(900, 600),
  theme: themeSchema("nature"),
  font_family: z.string().optional(),
  ...colorOverrideSchema.shape,
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
    output_filename,
  } = renderKnowledgeGraphSchema.parse(args);

  await onProgress?.(20, 100);

  const themeOverrides = buildThemeOverrides(
    { background_color, text_color, axis_color, split_line_color, palette, primary_color },
    theme
  );

  const nodes = z
    .array(nodeSchema)
    .parse(safeJsonParse(nodesRaw))
    .map((n) => ({ id: n.id, group: n.group ?? 0 }));
  let links = z
    .array(linkSchema)
    .parse(safeJsonParse(linksRaw))
    .map((l) => ({ source: l.source, target: l.target, relation: l.relation ?? "" }));

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

  const defaultName = `knowledge_graph_${Date.now()}`;
  const outputPath = await writeOutputFile(resolveOutputFilename(output_filename, defaultName, fileExt), content);

  await onProgress?.(100, 100);
  const formatLabel = output_format === "html" ? "HTML" : output_format === "png" ? "PNG" : "SVG";
  const summary = `Generated ${formatLabel} knowledge graph: ${nodes.length} entities, ${links.length} relationships\nFile path: ${outputPath}`;

  return { content: [{ type: "text" as const, text: summary }] };
}
