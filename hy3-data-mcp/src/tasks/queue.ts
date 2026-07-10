import type {
  QueuedMessage,
  TaskMessageQueue,
} from "@modelcontextprotocol/sdk/experimental/tasks/interfaces.js";

export class InMemoryTaskMessageQueue implements TaskMessageQueue {
  private queues = new Map<string, QueuedMessage[]>();

  async enqueue(
    taskId: string,
    message: QueuedMessage,
    _sessionId?: string,
    maxSize?: number
  ): Promise<void> {
    let queue = this.queues.get(taskId);
    if (!queue) {
      queue = [];
      this.queues.set(taskId, queue);
    }
    if (maxSize !== undefined && queue.length >= maxSize) {
      throw new Error(`Task message queue full for task ${taskId}`);
    }
    queue.push(message);
  }

  async dequeue(taskId: string, _sessionId?: string): Promise<QueuedMessage | undefined> {
    const queue = this.queues.get(taskId);
    if (!queue || queue.length === 0) {
      return undefined;
    }
    return queue.shift();
  }

  async dequeueAll(taskId: string, _sessionId?: string): Promise<QueuedMessage[]> {
    const queue = this.queues.get(taskId);
    if (!queue) {
      return [];
    }
    this.queues.delete(taskId);
    return queue;
  }
}
