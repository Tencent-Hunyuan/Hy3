import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { AnySchema } from "@modelcontextprotocol/sdk/server/zod-compat.js";
import type { RequestHandlerExtra, RequestTaskStore } from "@modelcontextprotocol/sdk/shared/protocol.js";
import type { ServerNotification, ServerRequest } from "@modelcontextprotocol/sdk/types.js";
import type { CallToolResult, GetTaskResult } from "@modelcontextprotocol/sdk/types.js";
import { z } from "zod";
import { Hy3Client } from "../client.js";
import { runToolAsTask } from "../tasks/runner.js";
import { analyzeDefinition, runAnalyze, analyzeSchema } from "./analyze.js";
import { analyzeReportDefinition, runAnalyzeReport, analyzeReportSchema } from "./analyzeReport.js";
import { extractDocumentDefinition, runExtractDocument, extractDocumentSchema } from "./extractDocument.js";
import { planChartDefinition, runPlanChart, planChartSchema } from "./planChart.js";
import { planDashboardDefinition, runPlanDashboard, planDashboardSchema } from "./planDashboard.js";
import { planKnowledgeGraphDefinition, runPlanKnowledgeGraph, planKnowledgeGraphSchema } from "./planKnowledgeGraph.js";
import { planWordcloudDefinition, runPlanWordcloud, planWordcloudSchema } from "./planWordcloud.js";
import { renderChartDefinition, runRenderChart, renderChartSchema } from "./renderChart.js";
import { renderDashboardDefinition, runRenderDashboard, renderDashboardSchema } from "./renderDashboard.js";
import { renderKnowledgeGraphDefinition, runRenderKnowledgeGraph, renderKnowledgeGraphSchema } from "./renderKnowledgeGraph.js";
import { renderWordcloudDefinition, runRenderWordcloud, renderWordcloudSchema } from "./renderWordcloud.js";

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
    name: renderChartDefinition.name,
    description: renderChartDefinition.description,
    schema: renderChartSchema,
    run: runRenderChart,
  },
  {
    name: renderWordcloudDefinition.name,
    description: renderWordcloudDefinition.description,
    schema: renderWordcloudSchema,
    run: runRenderWordcloud,
  },
  {
    name: renderKnowledgeGraphDefinition.name,
    description: renderKnowledgeGraphDefinition.description,
    schema: renderKnowledgeGraphSchema,
    run: runRenderKnowledgeGraph,
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
    name: analyzeDefinition.name,
    description: analyzeDefinition.description,
    schema: analyzeSchema,
    run: runAnalyze as ToolRunner,
  },
  {
    name: analyzeReportDefinition.name,
    description: analyzeReportDefinition.description,
    schema: analyzeReportSchema,
    run: runAnalyzeReport as ToolRunner,
  },
  {
    name: planChartDefinition.name,
    description: planChartDefinition.description,
    schema: planChartSchema,
    run: runPlanChart as ToolRunner,
  },
  {
    name: planDashboardDefinition.name,
    description: planDashboardDefinition.description,
    schema: planDashboardSchema,
    run: runPlanDashboard as ToolRunner,
  },
  {
    name: planWordcloudDefinition.name,
    description: planWordcloudDefinition.description,
    schema: planWordcloudSchema,
    run: runPlanWordcloud as ToolRunner,
  },
  {
    name: planKnowledgeGraphDefinition.name,
    description: planKnowledgeGraphDefinition.description,
    schema: planKnowledgeGraphSchema,
    run: runPlanKnowledgeGraph as ToolRunner,
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
