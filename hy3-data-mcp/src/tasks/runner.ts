import type { RequestTaskStore } from "@modelcontextprotocol/sdk/shared/protocol.js";
import type { CallToolResult } from "@modelcontextprotocol/sdk/types.js";
import { Hy3Client } from "../client.js";
import { handleToolCall } from "../tools/index.js";

const CANCEL_CHECK_INTERVAL_MS = 1_000;
const STATUS_UPDATE_INTERVAL_MS = 500;

export async function runToolAsTask(
  taskId: string,
  toolName: string,
  args: unknown,
  client: Hy3Client,
  taskStore: RequestTaskStore,
  signal?: AbortSignal
): Promise<void> {
  const updateStatus = async (message: string) => {
    try {
      await taskStore.updateTaskStatus(taskId, "working", message);
    } catch {
      // ignore status update errors
    }
  };

  // 任务级 AbortController：客户端取消任务时会触发
  const taskController = new AbortController();
  const taskSignal = taskController.signal;

  // 如果外部 signal 已触发，也取消任务
  signal?.addEventListener("abort", () => taskController.abort(), { once: true });

  // 轮询任务是否被取消
  const cancelChecker = setInterval(async () => {
    try {
      const task = await taskStore.getTask(taskId);
      if (task?.status === "cancelled") {
        taskController.abort();
      }
    } catch {
      // ignore polling errors
    }
  }, CANCEL_CHECK_INTERVAL_MS);

  // 流式输出缓冲：定期把最新累积输出写入任务状态
  let streamedOutput = "";
  let lastStatusUpdate = 0;
  const onOutput = (chunk: string) => {
    streamedOutput += chunk;
    const now = Date.now();
    if (now - lastStatusUpdate > STATUS_UPDATE_INTERVAL_MS) {
      lastStatusUpdate = now;
      // 状态消息保留最近 2000 字符，避免过长
      const preview = streamedOutput.slice(-2000);
      updateStatus(preview).catch(() => {});
    }
  };

  try {
    await updateStatus("开始执行工具...");

    const onProgress = async (progress: number, total?: number) => {
      const message = total
        ? `执行中 ${progress}/${total}`
        : `执行中 ${progress}%`;
      await updateStatus(message);
    };

    if (taskSignal.aborted) {
      throw new Error("Task was cancelled before execution");
    }

    const result = await handleToolCall(toolName, args, client, onProgress, taskSignal, onOutput);
    await taskStore.storeTaskResult(taskId, "completed", result);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    const errorResult: CallToolResult = {
      content: [{ type: "text", text: message }],
      isError: true,
    };
    await taskStore.storeTaskResult(taskId, "failed", errorResult);
  } finally {
    clearInterval(cancelChecker);
  }
}
