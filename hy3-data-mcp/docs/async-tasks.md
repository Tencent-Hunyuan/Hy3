# Hy3 Data MCP 异步任务改造方案

## 1. 我们要解决什么问题？

改造前，`hy3-data-mcp` 的工具（如 `hy3_document_summary`、`hy3_data_visualize`、`hy3_data_report` 等）几乎都是**同步调用大模型**完成分析。2.0 架构将它们拆分为 `hy3_plan_*`（调用 LLM 做规划）和 `hy3_render_*`（确定性渲染）两类工具：

```ts
const response = await openai.chat.completions.create({
  model: "hy3-preview",
  stream: false, // 必须等模型全部生成完才返回
  ...
});
```

问题在于：

- 大模型生成报告、分析数据、写 HTML 等任务动辄需要 **10 秒 ~ 数分钟**。
- MCP 协议规定，客户端对单次 `tools/call` 的默认等待时间只有 **60 秒**（`DEFAULT_REQUEST_TIMEOUT_MSEC = 60000`）。
- 服务端没有主动把“我要开始跑了”这个信息提前告诉客户端，导致客户端傻傻等到 60 秒后报超时。

结果就是：文档稍微长一点、问题稍微复杂一点，工具调用就超时失败。

## 2. 本次改造的目标方案

**把重工具改造成 MCP Task（任务）机制下的异步调用**：

1. 客户端仍然调用 `tools/call`，但请求里带一个任务增强标记。
2. 服务端收到后**不立即执行大模型**，而是创建一个任务，立刻返回 `taskId` 给客户端。
3. 服务端在后台慢慢跑大模型分析。
4. 客户端用 `tasks/get` 轮询任务状态（`working` → `completed` / `failed`）。
5. 任务完成后，客户端用 `tasks/result` 取回真正的工具结果。
6. 如果客户端不想等了，可以调用 `tasks/cancel` 取消任务。

通俗理解：

> 以前像去餐厅点完菜必须在柜台站着等，厨师做好了才能走；<br>
> 现在像扫码取号，拿到号（taskId）就能去旁边坐着，做好了叫号（轮询状态），再过来取餐（取结果）。

## 3. 什么是 MCP 高阶 API（McpServer）？

### 3.1 当前用的是低层 API

改造前，项目用的是 `@modelcontextprotocol/sdk` 里的低层 `Server` 类：

```ts
import { Server } from "@modelcontextprotocol/sdk/server/index.js";

const server = new Server(
  { name: "hy3-data-mcp", version: "0.1.0" },
  { capabilities: { tools: {} } }
);

// 所有事情都要自己写
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: TOOL_DEFINITIONS,
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  return handleToolCall(name, args, client);
});
```

它的特点是：

- 自己维护 `TOOL_DEFINITIONS` 数组；
- 自己根据 `name` 路由到对应的工具函数；
- 自己用 Zod 校验参数；
- 自己处理 MCP 协议细节。

### 3.2 高阶 API：McpServer

MCP SDK 还提供了一个更上层的封装 `McpServer`：

```ts
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

const server = new McpServer({ name: "hy3-data-mcp", version: "0.2.1" });

server.tool(
  "hy3_analyze",
  "Analyze extracted text with Hy3",
  {
    file_path: z.string(),
    question: z.string().optional(),
  },
  async (args, extra) => {
    // args 已经被 SDK 校验和解析过了
    const result = await runAnalyzeText(args, client);
    return { content: [{ type: "text", text: result }] };
  }
);
```

高阶 API 帮我们做了：

| 低层 Server 要手写 | McpServer 自动处理 |
|---|---|
| 维护 `TOOL_DEFINITIONS` | 自动收集所有 `server.tool()` 注册的工具 |
| 手动把 Zod schema 转成 JSON Schema | `ListTools` 时自动转换 |
| 手动校验 `arguments` | 调用回调前自动 `safeParseAsync` |
| 手动路由 `name → handler` | 按注册名自动路由 |
| 手动声明 capabilities | 注册工具后自动声明 `tools` 能力 |

> SDK 的低层 `Server` 文档上已经标注 `@deprecated Use McpServer instead`，说明高阶 API 是官方推荐方向。

### 3.3 McpServer 的任务支持

`McpServer.experimental.tasks` 提供了把工具注册成“任务型工具”的能力：

```ts
server.experimental.tasks.registerToolTask(
  "hy3_analyze",
  {
    description: "Analyze extracted text with Hy3",
    inputSchema: { text: z.string(), question: z.string().optional() },
    execution: { taskSupport: "optional" },
  },
  {
    createTask: async (args, extra) => {
      // 1. 创建任务
      const task = await extra.taskStore.createTask(
        { ttl: 300000 },
        extra.requestId,
        { method: "tools/call", params: { name: "hy3_analyze", arguments: args } }
      );

      // 2. 后台执行，不 await
      runToolInBackground(task.taskId, args, extra.taskStore, extra.signal);

      // 3. 立刻返回 taskId
      return { task };
    },

    getTask: async (_args, extra) => {
      return extra.taskStore.getTask(extra.taskId);
    },

    getTaskResult: async (_args, extra) => {
      return extra.taskStore.getTaskResult(extra.taskId);
    },
  }
);
```

这样注册后：

- 普通客户端调用 `tools/call` → 走同步路径，直接返回结果（兼容现有行为）。
- 任务感知的客户端调用 `tools/call` 并带 `task` 参数 → 走 `createTask`，立即返回 `taskId`。
- `tasks/get`、`tasks/list`、`tasks/cancel`、`tasks/result` 这些协议请求由 SDK 自动处理，不需要我们写 handler。

## 4. 改造后的架构

```
┌─────────────────┐      tools/call (with task)      ┌─────────────────┐
│   MCP Client    │ ────────────────────────────────→ │                 │
│                 │ ←──────── taskId / task ───────── │   hy3-data-mcp  │
│                 │                                   │   (McpServer)   │
│                 │ ───────── tasks/get ─────────────→│                 │
│                 │ ←────── status: working ──────────│                 │
│                 │                                   │  ┌───────────┐  │
│                 │ ───────── tasks/get ─────────────→│  │ TaskStore │  │
│                 │ ←────── status: completed ────────│  │ (memory)  │  │
│                 │                                   │  └───────────┘  │
│                 │ ───────── tasks/result ──────────→│        ↕        │
│                 │ ←──────── CallToolResult ────────│  ┌───────────┐  │
│                 │                                   │  │  Hy3 LLM  │  │
└─────────────────┘                                   │  └───────────┘  │
                                                      └─────────────────┘
```

核心组件：

| 组件 | 作用 |
|---|---|
| `McpServer` | 高阶 MCP 服务器，自动处理工具注册、校验、任务协议 |
| `TaskStore` | 保存任务状态、结果；实现 `createTask` / `getTask` / `listTasks` / `updateTaskStatus` / `storeTaskResult` |
| `TaskMessageQueue` | MCP 任务侧信道消息队列，SDK 需要 |
| `Task Runner` | 后台执行实际工具逻辑，更新任务状态并存储结果 |
| `Hy3Client` | 扩展支持 `AbortSignal`，让取消任务时能中断模型调用 |

## 5. 客户端怎么用？

如果客户端支持 MCP Task（如使用 `client.experimental.tasks.callToolStream`）：

```ts
import { Client } from "@modelcontextprotocol/sdk/client/index.js";

const stream = client.experimental.tasks.callToolStream(
  {
    name: "hy3_analyze",
    arguments: { text: "...", question: "总结核心风险" },
  },
  CallToolResultSchema,
  { task: { ttl: 300000 } } // 任务保留 5 分钟
);

for await (const message of stream) {
  switch (message.type) {
    case "taskCreated":
      console.log("任务已创建:", message.task.taskId);
      break;
    case "taskStatus":
      console.log("当前状态:", message.task.status, message.task.statusMessage);
      break;
    case "result":
      console.log("最终结果:", message.result);
      break;
    case "error":
      console.error("出错了:", message.error);
      break;
  }
}
```

如果客户端不支持 Task（比如旧版 Claude Desktop），仍然可以普通调用 `tools/call`，服务端会同步执行并返回结果，和改造前一致。

## 6. 注意事项

1. **实验性 API**：MCP Task/Stream 机制目前还是 `experimental`，SDK 后续版本可能会调整接口。
2. **内存存储**：第一版用内存 `TaskStore`，进程重启任务会丢失。后续如果需要持久化，可以换成 Redis/数据库实现。
3. **TTL 清理**：完成的任务要设置 TTL（如 5 分钟），避免内存无限增长。
4. **取消信号**：需要把 `AbortSignal` 透传给 OpenAI SDK 调用，才能真正中断模型推理，而不是只改状态。
5. **同步兼容**：所有工具仍然保留同步执行路径，保证不支持 Task 的客户端也能正常工作。
