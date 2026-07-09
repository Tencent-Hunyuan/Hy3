import { Hy3Client } from "../client.js";
import { dataDashboardDefinition, runDataDashboard } from "./dataDashboard.js";
import { dataInsightDefinition, runDataInsight } from "./dataInsight.js";
import { dataVisualizeDefinition, runDataVisualize } from "./dataVisualize.js";
import { documentSummaryDefinition, runDocumentSummary } from "./documentSummary.js";
import { documentVisualizeDefinition, runDocumentVisualize } from "./documentVisualize.js";
import { knowledgeGraphDefinition, runKnowledgeGraph } from "./knowledgeGraph.js";
import { wordcloudDefinition, runWordcloud } from "./wordcloud.js";

export const TOOL_DEFINITIONS = [
  dataVisualizeDefinition,
  wordcloudDefinition,
  knowledgeGraphDefinition,
  dataDashboardDefinition,
  dataInsightDefinition,
  documentSummaryDefinition,
  documentVisualizeDefinition,
];

export async function handleToolCall(
  name: string,
  args: unknown,
  client: Hy3Client
): Promise<{ content: Array<{ type: "text"; text: string }> }> {
  switch (name) {
    case "hy3_data_visualize":
      return runDataVisualize(args, client);
    case "hy3_wordcloud":
      return runWordcloud(args, client);
    case "hy3_knowledge_graph":
      return runKnowledgeGraph(args, client);
    case "hy3_data_dashboard":
      return runDataDashboard(args, client);
    case "hy3_data_insight":
      return runDataInsight(args, client);
    case "hy3_document_summary":
      return runDocumentSummary(args, client);
    case "hy3_document_visualize":
      return runDocumentVisualize(args, client);
    default:
      throw new Error(`Unknown tool: ${name}`);
  }
}
