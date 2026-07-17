# Using Hy3 with Cursor

> 🌐 中文版本： [cursor.md](cursor.md)

## Introduction

[Cursor](https://cursor.sh) is a VS Code-based, AI-native IDE with built-in code completion (Tab) and conversational coding (Composer). It supports connecting to **any OpenAI-compatible API**, so Hy3 integrates seamlessly.

## Use Cases

- Everyday coding, refactoring, and debugging
- Project-level Agent: let Hy3 read and edit multiple files
- Leverage Hy3's 256K context to work with large codebases

## Requirements

| Item | Requirement |
|:---|:---|
| Cursor version | ≥ 0.42 (latest recommended) |
| OS | macOS / Windows / Linux |
| Hy3 service | Self-hosted vLLM/SGLang service, or OpenRouter proxy |

## Configuration

Open Cursor → `Settings` → `Models` → the `OpenAI API Key` section, and fill in the following:

### Option 1: self-hosted service

```json
{
  "cursor.general.enableOpenAIAPIKey": true,
  "openAiApiKey": "your-api-key",
  "cursor.general.openAiBaseUrl": "https://tokenhub.tencentmaas.com/v1",
  "cursor.general.openAiModel": "hyde"
}
```

> ⚠️ **Note**: Cursor requires you to manually check/add the custom model name in the `Settings` → `Models` panel.

### Option 2: OpenRouter proxy

```json
{
  "cursor.general.enableOpenAIAPIKey": true,
  "openAiApiKey": "sk-or-v1-your-key",
  "cursor.general.openAiBaseUrl": "https://openrouter.ai/api/v1",
  "cursor.general.openAiModel": "tencent/hy3"
}
```

### Key parameter mapping

| Hy3 capability | How it shows up in Cursor |
|:---|:---|
| `reasoning_effort=high` | Kicks in automatically for complex logic in Composer |
| Function Call / Tool Use | Invoked automatically via Agent mode |
| 256K context | Fully utilized for long-file / multi-file edits |
| `temperature=0.9` | Set in the model configuration |

## End-to-End Demo: Refactor an Express Middleware with Hy3

### Scenario

You have a legacy Express error-handling middleware that needs to be refactored to TypeScript with added type safety.

### Steps

1. **Open Composer**: press `Ctrl/Cmd + I` to open Cursor Composer
2. **Select the model**: in the bottom model selector, switch to `hy3` (or `tencent/hy3`)
3. **Enter the prompt**:

```
Refactor the currently open error-handler.js to TypeScript:
1. Strict type definitions (request, response, error types)
2. Distinguish error response formats for development vs. production
3. Keep the original logging logic
4. Add JSDoc comments
```

4. **Hy3 response**:

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

5. **Apply the change**: click `Apply` in Composer to write it into the file with one click

### Expected result

- Hy3 automatically analyzes the original JS code context
- Generates a type-safe TS replacement
- Preserves the original business logic
- Includes complete JSDoc comments

## Common Notes

| Issue | Cause | Solution |
|:---|:---|:---|
| Hy3 not in the model list | Cursor only shows built-in models by default | Manually add `hy3` in Settings → Models |
| `invalid_api_key` | Wrong API Key format or base_url | Use `EMPTY` for self-hosted, full Key for proxy |
| Slow responses | High GPU load on the self-hosted service | Check the vLLM service status, or switch to OpenRouter |
| Tab completion not working | Tab completion has a separate model setting | Set the Completion Model separately in Settings |
| Composer Apply fails | Model output format doesn't meet Cursor's requirements | Ensure the `hy_v3` tool-call-parser is used (self-hosted) |
| Long-conversation context lost | Exceeds the current conversation window | For very long tasks, split into multiple Composer sessions |


[← Back to Index](../README.en.md)
