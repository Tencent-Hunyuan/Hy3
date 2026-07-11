import { randomUUID } from "crypto";
import type {
  CreateTaskOptions,
  TaskStore,
} from "@modelcontextprotocol/sdk/experimental/tasks/interfaces.js";
import type { Request, RequestId, Result, Task } from "@modelcontextprotocol/sdk/types.js";

interface StoredTask {
  task: Task;
  result?: Result;
}

export class InMemoryTaskStore implements TaskStore {
  private tasks = new Map<string, StoredTask>();
  private cleanupInterval?: ReturnType<typeof setInterval>;

  constructor(private readonly defaultTtlMs = 300_000) {
    // 每 60 秒清理一次过期任务
    this.cleanupInterval = setInterval(() => this.cleanupExpired(), 60_000);
    this.cleanupInterval.unref?.();
  }

  async createTask(
    taskParams: CreateTaskOptions,
    _requestId: RequestId,
    _request: Request,
    _sessionId?: string
  ): Promise<Task> {
    const now = new Date().toISOString();
    const ttl = taskParams.ttl ?? this.defaultTtlMs;
    const task: Task = {
      taskId: randomUUID(),
      status: "working",
      statusMessage: "任务已创建",
      createdAt: now,
      lastUpdatedAt: now,
      ttl,
      pollInterval: taskParams.pollInterval ?? 1_000,
    };
    this.tasks.set(task.taskId, { task });
    return task;
  }

  async getTask(taskId: string, _sessionId?: string): Promise<Task | null> {
    const stored = this.tasks.get(taskId);
    return stored ? this.cloneTask(stored.task) : null;
  }

  async listTasks(
    _cursor?: string,
    _sessionId?: string
  ): Promise<{ tasks: Task[]; nextCursor?: string }> {
    const tasks = Array.from(this.tasks.values()).map((s) => this.cloneTask(s.task));
    return { tasks };
  }

  async updateTaskStatus(
    taskId: string,
    status: Task["status"],
    statusMessage?: string,
    _sessionId?: string
  ): Promise<void> {
    const stored = this.tasks.get(taskId);
    if (!stored) {
      throw new Error(`Task not found: ${taskId}`);
    }
    stored.task = {
      ...stored.task,
      status,
      ...(statusMessage !== undefined && { statusMessage }),
      lastUpdatedAt: new Date().toISOString(),
    };
    this.tasks.set(taskId, stored);
  }

  async storeTaskResult(
    taskId: string,
    status: "completed" | "failed",
    result: Result,
    _sessionId?: string
  ): Promise<void> {
    const stored = this.tasks.get(taskId);
    if (!stored) {
      throw new Error(`Task not found: ${taskId}`);
    }
    stored.task = {
      ...stored.task,
      status,
      lastUpdatedAt: new Date().toISOString(),
    };
    stored.result = result;
    this.tasks.set(taskId, stored);
  }

  async getTaskResult(taskId: string, _sessionId?: string): Promise<Result> {
    const stored = this.tasks.get(taskId);
    if (!stored || !stored.result) {
      throw new Error(`Task result not found: ${taskId}`);
    }
    return stored.result;
  }

  private cloneTask(task: Task): Task {
    return { ...task };
  }

  private cleanupExpired(): void {
    const now = Date.now();
    for (const [taskId, stored] of this.tasks.entries()) {
      if (stored.task.ttl === null) continue;
      const createdAt = new Date(stored.task.createdAt).getTime();
      if (now - createdAt > stored.task.ttl) {
        this.tasks.delete(taskId);
      }
    }
  }

  dispose(): void {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
      this.cleanupInterval = undefined;
    }
  }
}
