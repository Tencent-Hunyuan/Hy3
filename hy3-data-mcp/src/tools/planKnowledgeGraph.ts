import { z } from "zod";
import { extname } from "path";
import { Hy3Client } from "../client.js";
import { askHy3, loadDataTable, loadInputText, resolveLanguage, sampleText } from "../utils.js";
import type { ProgressReporter } from "./index.js";

export const planKnowledgeGraphDefinition = {
  name: "hy3_plan_knowledge_graph",
  description:
    "Use Hy3 to extract entities and relationships from text or a file. Returns JSON {nodes, links} that can be passed to hy3_render_knowledge_graph.",
  inputSchema: {
    type: "object" as const,
    properties: {
      text: { type: "string", description: "Raw text to analyze." },
      file_path: { type: "string", description: "Path to a text, CSV, JSON or XLSX file." },
      max_entities: {
        type: "number",
        description: "Maximum number of entities.",
        default: 30,
      },
      language: {
        type: "string",
        enum: ["zh", "en", "auto"],
        description: "Language of the text.",
        default: "auto",
      },
    },
    required: [],
  },
};

export const planKnowledgeGraphSchema = z.object({
  text: z.string().optional(),
  file_path: z.string().optional(),
  max_entities: z.number().int().min(5).max(100).default(30),
  language: z.enum(["zh", "en", "auto"]).default("auto"),
});

export interface KnowledgeGraphPlan {
  nodes: { id: string; group: number }[];
  links: { source: string; target: string; relation: string }[];
}

export async function runPlanKnowledgeGraph(
  args: unknown,
  client: Hy3Client,
  onProgress?: ProgressReporter,
  signal?: AbortSignal,
  onOutput?: (chunk: string) => void
): Promise<{ content: Array<{ type: "text"; text: string }> }> {
  const { text, file_path, max_entities, language } = planKnowledgeGraphSchema.parse(args);

  if (!text && !file_path) {
    throw new Error("One of text or file_path is required");
  }

  await onProgress?.(10, 100);

  let inputText: string;
  if (text) {
    inputText = text;
  } else {
    const ext = extname(file_path!);
    if (ext === ".csv" || ext === ".json" || ext === ".jsonl" || ext === ".xlsx" || ext === ".xls") {
      const table = await loadDataTable(file_path!);
      const targetColumn =
        table.columns.find((c) =>
          /text|content|comment|review|description|描述|内容|评论/i.test(c)
        ) || table.columns[0];
      inputText = table.rows.map((row) => String(row[targetColumn] ?? "")).join("\n");
    } else {
      inputText = await loadInputText({ file_path: file_path! });
    }
  }

  const resolvedLanguage = resolveLanguage(language, inputText);
  await onProgress?.(30, 100);

  const system =
    resolvedLanguage === "zh"
      ? `你是一位知识图谱专家。请从以下文本中提取实体和关系。以纯 JSON 返回：{"nodes": [{"id": "实体名", "group": 1}, ...], "links": [{"source": "实体A", "target": "实体B", "relation": "关系"}, ...]}。实体最多 ${max_entities} 个。不要输出任何额外文字。`
      : `You are a knowledge-graph expert. Extract entities and relationships from the text below. Return pure JSON: {"nodes": [{"id": "entity name", "group": 1}, ...], "links": [{"source": "entity A", "target": "entity B", "relation": "relationship"}, ...]}. At most ${max_entities} entities. No extra text.`;

  await onProgress?.(60, 100);
  const answer = await askHy3(client, system, sampleText(inputText), signal, onOutput);
  await onProgress?.(90, 100);

  let graph: KnowledgeGraphPlan;
  try {
    graph = JSON.parse(answer);
  } catch {
    graph = { nodes: [], links: [] };
  }

  const nodeIds = new Set(graph.nodes.map((n) => n.id));
  graph.links = graph.links.filter((l) => nodeIds.has(l.source) && nodeIds.has(l.target));

  await onProgress?.(100, 100);
  return { content: [{ type: "text" as const, text: JSON.stringify(graph, null, 2) }] };
}
