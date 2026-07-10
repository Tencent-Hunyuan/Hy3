import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { AnySchema } from "@modelcontextprotocol/sdk/server/zod-compat.js";
import type { RequestHandlerExtra, RequestTaskStore } from "@modelcontextprotocol/sdk/shared/protocol.js";
import type { ServerNotification, ServerRequest } from "@modelcontextprotocol/sdk/types.js";
import type { CallToolResult, GetTaskResult } from "@modelcontextprotocol/sdk/types.js";
import { z } from "zod";
import { Hy3Client } from "../client.js";
import { runToolAsTask } from "../tasks/runner.js";
import { analyzeTextDefinition, runAnalyzeText, analyzeTextSchema } from "./analyzeText.js";
import { designDashboardDefinition, runDesignDashboard, designDashboardSchema } from "./designDashboard.js";
import { renderDashboardDefinition, runRenderDashboard, renderDashboardSchema } from "./renderDashboard.js";
import { dataInsightDefinition, runDataInsight, dataInsightSchema } from "./dataInsight.js";
import { dataReportDefinition, runDataReport, dataReportSchema } from "./dataReport.js";
import { dataVisualizeDefinition, runDataVisualize, dataVisualizeSchema } from "./dataVisualize.js";
import { extractDocumentDefinition, runExtractDocument, extractDocumentSchema } from "./extractDocument.js";
import { knowledgeGraphDefinition, runKnowledgeGraph, knowledgeGraphSchema } from "./knowledgeGraph.js";
import { wordcloudDefinition, runWordcloud, wordcloudSchema } from "./wordcloud.js";

export type ProgressReporter = (progress: number, total?: number) => Promise<void> | void;

type ToolRunner = (
  args: unknown,
  client: Hy3Client,
  onProgress?: ProgressReporter,
  signal?: AbortSignal,
  onOutput?: (chunk: string) => void
) => Promise<CallToolResult>;

interface StaticToolRegistration {
  name: string;
  description: string;
  schema: z.ZodTypeAny;
  run: (args: unknown, onProgress?: ProgressReporter) => Promise<CallToolResult>;
}

interface LlmToolRegistration {
  name: string;
  description: string;
  schema: z.ZodTypeAny;
  run: ToolRunner;
}

const staticTools = (): StaticToolRegistration[] => [
  {
    name: extractDocumentDefinition.name,
    description: extractDocumentDefinition.description,
    schema: extractDocumentSchema,
    run: runExtractDocument,
  },
  {
    name: renderDashboardDefinition.name,
    description: renderDashboardDefinition.description,
    schema: renderDashboardSchema,
    run: runRenderDashboard,
  },
];

const llmTools = (): LlmToolRegistration[] => [
  {
    name: analyzeTextDefinition.name,
    description: analyzeTextDefinition.description,
    schema: analyzeTextSchema,
    run: runAnalyzeText as ToolRunner,
  },
  {
    name: dataVisualizeDefinition.name,
    description: dataVisualizeDefinition.description,
    schema: dataVisualizeSchema,
    run: runDataVisualize as ToolRunner,
  },
  {
    name: wordcloudDefinition.name,
    description: wordcloudDefinition.description,
    schema: wordcloudSchema,
    run: runWordcloud as ToolRunner,
  },
  {
    name: knowledgeGraphDefinition.name,
    description: knowledgeGraphDefinition.description,
    schema: knowledgeGraphSchema,
    run: runKnowledgeGraph as ToolRunner,
  },
  {
    name: designDashboardDefinition.name,
    description: designDashboardDefinition.description,
    schema: designDashboardSchema,
    run: runDesignDashboard as ToolRunner,
  },
  {
    name: dataReportDefinition.name,
    description: dataReportDefinition.description,
    schema: dataReportSchema,
    run: runDataReport as ToolRunner,
  },
  {
    name: dataInsightDefinition.name,
    description: dataInsightDefinition.description,
    schema: dataInsightSchema,
    run: runDataInsight as ToolRunner,
  },
];

export async function handleToolCall(
  name: string,
  args: unknown,
  client: Hy3Client,
  onProgress?: ProgressReporter,
  signal?: AbortSignal,
  onOutput?: (chunk: string) => void
): Promise<CallToolResult> {
  const staticTool = staticTools().find((t) => t.name === name);
  if (staticTool) {
    return staticTool.run(args, onProgress);
  }
  const tool = llmTools().find((t) => t.name === name);
  if (!tool) {
    throw new Error(`Unknown tool: ${name}`);
  }
  return tool.run(args, client, onProgress, signal, onOutput);
}

export function registerTools(server: McpServer, client: Hy3Client) {
  // 静态工具：不走 Task/Stream，直接同步返回
  for (const tool of staticTools()) {
    server.registerTool(
      tool.name,
      {
        description: tool.description,
        inputSchema: tool.schema as AnySchema,
      },
      async (
        args: unknown,
        _extra: RequestHandlerExtra<ServerRequest, ServerNotification>
      ) => {
        return tool.run(args);
      }
    );
  }

  // LLM 工具：支持 Task/Stream 异步执行
  for (const tool of llmTools()) {
    server.experimental.tasks.registerToolTask(
      tool.name,
      {
        description: tool.description,
        inputSchema: tool.schema as AnySchema,
        execution: { taskSupport: "optional" },
      },
      {
        createTask: async (args, extra) => {
          const taskStore = extra.taskStore as RequestTaskStore;
          const task = await taskStore.createTask({
            ttl: 300_000,
            pollInterval: 1_000,
          });
          runToolAsTask(task.taskId, tool.name, args, client, taskStore, extra.signal);
          return { task };
        },
        getTask: async (_args, extra) => {
          const task = await extra.taskStore.getTask(extra.taskId);
          if (!task) {
            throw new Error(`Task not found: ${extra.taskId}`);
          }
          return task as GetTaskResult;
        },
        getTaskResult: async (_args, extra) => {
          const result = await extra.taskStore.getTaskResult(extra.taskId);
          return result as CallToolResult;
        },
      }
    );
  }
}
