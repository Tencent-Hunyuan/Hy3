# 在 Cursor 中使用 Hy3

> 🌐 English version: [cursor.en.md](cursor.en.md)

## 工具简介

[Cursor](https://cursor.sh) 是基于 VS Code 的 AI 原生 IDE，内置了代码补全（Tab）和对话式编程（Composer）能力。它支持接入**任何 OpenAI 兼容 API**，因此可以无缝集成 Hy3。

## 适用场景

- 日常编码、重构、调试
- 全项目级 Agent：让 Hy3 读取并修改多文件
- 利用 Hy3 的 256K 上下文处理大型代码库

## 版本要求

| 项 | 要求 |
|:---|:---|
| Cursor 版本 | ≥ 0.42（推荐最新版） |
| 操作系统 | macOS / Windows / Linux |
| Hy3 服务 | 自建 vLLM/SGLang 服务，或 OpenRouter 代理 |

## 配置项

打开 Cursor → `Settings` → `Models` → `OpenAI API Key` 区域，填入以下配置：

### 方案一：自建服务

```json
{
  "cursor.general.enableOpenAIAPIKey": true,
  "openAiApiKey": "your-api-key",
  "cursor.general.openAiBaseUrl": "https://tokenhub.tencentmaas.com/v1",
  "cursor.general.openAiModel": "hyde"
}
```

> ⚠️ **注意**：Cursor 需要在 `Settings` → `Models` 面板中手动勾选/添加自定义模型名称。

### 方案二：OpenRouter 代理

```json
{
  "cursor.general.enableOpenAIAPIKey": true,
  "openAiApiKey": "sk-or-v1-你的密钥",
  "cursor.general.openAiBaseUrl": "https://openrouter.ai/api/v1",
  "cursor.general.openAiModel": "tencent/hy3"
}
```

### 关键参数映射

| Hy3 能力 | Cursor 中的表现 |
|:---|:---|
| `reasoning_effort=high` | Composer 中处理复杂逻辑时自动生效 |
| Function Call / Tool Use | 通过 Agent 模式自动调用 |
| 256K 上下文 | 长文件/多文件编辑时充分利用 |
| `temperature=0.9` | 模型配置中设置 |

## 端到端 Demo：用 Hy3 重构一个 Express 中间件

### 场景

你有一个老旧的 Express 错误处理中间件，需要重构为 TypeScript 并增加类型安全。

### 步骤

1. **打开 Composer**：`Ctrl/Cmd + I` 打开 Cursor Composer
2. **选择模型**：在底部模型选择器中切换到 `hy3`（或 `tencent/hy3`）
3. **输入 Prompt**：

```
请把当前打开的 error-handler.js 重构为 TypeScript：
1. 严格类型定义（请求、响应、错误类型）
2. 区分开发/生产环境的错误返回格式
3. 保持原有日志记录逻辑
4. 添加 JSDoc 注释
```

4. **Hy3 响应**：

```typescript
import { Request, Response, NextFunction } from 'express';

interface AppError extends Error {
  statusCode?: number;
  isOperational?: boolean;
}

interface ErrorResponse {
  success: false;
  message: string;
  stack?: string;
}

/**
 * Global error handling middleware for Express.
 * Distinguishes between development and production error formats.
 */
export function errorHandler(
  err: AppError,
  _req: Request,
  res: Response,
  _next: NextFunction
): void {
  const statusCode = err.statusCode ?? 500;
  const isDev = process.env.NODE_ENV === 'development';

  console.error(`[${new Date().toISOString()}] ${statusCode} - ${err.message}`);

  const body: ErrorResponse = {
    success: false,
    message: isDev || err.isOperational 
      ? err.message 
      : 'Internal Server Error',
  };

  if (isDev && err.stack) {
    body.stack = err.stack;
  }

  res.status(statusCode).json(body);
}

/**
 * Wraps async route handlers to forward errors to the error handler.
 */
export function asyncHandler(
  fn: (req: Request, res: Response, next: NextFunction) => Promise<void>
) {
  return (req: Request, res: Response, next: NextFunction) => {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
}
```

5. **Apply 修改**：点击 Composer 中的 `Apply` 一键写入文件

### 预期效果

- Hy3 自动分析原 JS 代码上下文
- 生成类型安全的 TS 替代方案
- 保持原有业务逻辑不变
- 附带完整 JSDoc 注释

## 常见注意事项

| 问题 | 原因 | 解决方案 |
|:---|:---|:---|
| 模型列表中找不到 Hy3 | Cursor 默认只显示内置模型 | 在 Settings → Models 中手动添加 `hy3` |
| `invalid_api_key` | API Key 格式或 base_url 错误 | 确认自建服务用 `EMPTY`，代理用完整 Key |
| 响应速度慢 | 自建服务 GPU 负载高 | 检查 vLLM 服务状态，或切换到 OpenRouter |
| Tab 补全不生效 | Tab 补全有独立模型设置 | 在 Settings 中单独设置 Completion Model |
| Composer Apply 失败 | 模型输出格式不满足 Cursor 要求 | 确认使用 `hy_v3` tool-call-parser（自建服务） |
| 长对话上下文丢失 | 超出当前对话窗口 | 对于超长任务，分多个 Composer 会话进行 |


[← 返回索引](../README.md)
