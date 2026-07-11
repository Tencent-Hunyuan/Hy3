import { z } from "zod";
import { extname } from "path";
import { Hy3Client } from "../client.js";
import { askHy3Json } from "../llm-utils.js";
import { languageSchema, rawLanguageProperty } from "../schemas.js";
import { loadDataTable, loadInputText, resolveLanguage, sampleText, selectTextColumn } from "../utils.js";
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
      ...rawLanguageProperty("Language of the text."),
    },
    required: [],
  },
};

const plannedNodeSchema = z.object({ id: z.string().min(1), group: z.number().int().optional() });
const plannedLinkSchema = z.object({
  source: z.string().min(1),
  target: z.string().min(1),
  relation: z.string().optional(),
});
const graphOutputSchema = z.object({
  nodes: z.array(plannedNodeSchema),
  links: z.array(plannedLinkSchema),
});

export const planKnowledgeGraphSchema = z.object({
  text: z.string().optional(),
  file_path: z.string().optional(),
  max_entities: z.number().int().min(5).max(100).default(30),
  language: languageSchema,
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
      const targetColumn = selectTextColumn(table.columns, table.rows) || table.columns[0];
      inputText = table.rows.map((row) => String(row[targetColumn] ?? "")).join("\n");
    } else {
      inputText = await loadInputText({ file_path: file_path! });
    }
  }

  const resolvedLanguage = resolveLanguage(language, inputText);
  await onProgress?.(30, 100);

  const system =
    resolvedLanguage === "zh"
      ? `你是一位知识图谱专家。请从以下文本中提取实体和它们之间的关系。必须以纯 JSON 返回：{"nodes": [{"id": "实体名", "group": 1}, ...], "links": [{"source": "实体A", "target": "实体B", "relation": "关系描述"}, ...]}。links 不能为空，请至少根据文本中的主谓宾、因果关系、从属关系或共现关系提取 3-10 条关系。实体最多 ${max_entities} 个。不要输出任何额外文字。`
      : `You are a knowledge-graph expert. Extract entities and the relationships between them from the text below. You MUST return pure JSON: {"nodes": [{"id": "entity name", "group": 1}, ...], "links": [{"source": "entity A", "target": "entity B", "relation": "relationship description"}, ...]}. The links array must not be empty; extract at least 3-10 relationships based on subject-predicate-object, causation, attribution, or co-occurrence. At most ${max_entities} entities. No extra text.`;

  await onProgress?.(60, 100);

  let graph: KnowledgeGraphPlan;
  let warning = "";
  try {
    const parsed = await askHy3Json(client, system, sampleText(inputText), graphOutputSchema, { signal, onToken: onOutput });
    graph = {
      nodes: parsed.data.nodes.map((n) => ({ id: n.id, group: n.group ?? 0 })),
      links: parsed.data.links.map((l) => ({ source: l.source, target: l.target, relation: l.relation ?? "" })),
    };
  } catch {
    graph = { nodes: [], links: [] };
    warning = resolvedLanguage === "zh" ? "模型输出解析失败，将使用共现关系兜底。" : "Model output could not be parsed; using co-occurrence fallback.";
  }

  const nodeIds = new Set(graph.nodes.map((n) => n.id));
  graph.links = graph.links.filter((l) => nodeIds.has(l.source) && nodeIds.has(l.target));

  if (graph.links.length === 0 && graph.nodes.length > 1) {
    graph.links = fallbackCooccurrenceLinks(
      graph.nodes,
      inputText,
      resolvedLanguage === "zh" ? "共现" : "co-occur"
    );
  }

  await onProgress?.(100, 100);
  const result: KnowledgeGraphPlan & { _warning?: string } = graph;
  if (warning) result._warning = warning;
  return { content: [{ type: "text" as const, text: JSON.stringify(result, null, 2) }] };
}

function fallbackCooccurrenceLinks(
  nodes: { id: string; group: number }[],
  text: string,
  relation: string
): { source: string; target: string; relation: string }[] {
  const nodeIds = nodes.map((n) => n.id);
  const seen = new Set<string>();
  const links: { source: string; target: string; relation: string }[] = [];
  const sentences = text.split(/[。！？\n.!?]+/).filter((s) => s.trim().length > 0);

  for (const sentence of sentences) {
    const present = nodeIds.filter((id) => sentence.includes(id));
    for (let i = 0; i < present.length; i++) {
      for (let j = i + 1; j < present.length; j++) {
        const a = present[i];
        const b = present[j];
        const key = a < b ? `${a}|${b}` : `${b}|${a}`;
        if (seen.has(key)) continue;
        seen.add(key);
        links.push({ source: a, target: b, relation });
      }
    }
  }

  return links;
}
