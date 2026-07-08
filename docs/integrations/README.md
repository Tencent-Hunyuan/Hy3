# Hy3 主流 AI 产品接入指南

本目录面向终端用户，说明如何在常见 AI 产品、IDE、VS Code 插件和低代码平台中使用 Hy3，并给出一个基于 Hy3 的小作品 demo 方案。

## 通用配置

Hy3 API 使用 OpenAI Compatible 协议。只要工具支持自定义 OpenAI 兼容服务，一般都可以按下表配置。

| 配置项 | 值 |
| --- | --- |
| Base URL | `https://tokenhub.tencentmaas.com/v1` |
| Model | `hy3-preview` |
| Protocol | OpenAI Compatible |
| API Key | TokenHub API Key |
| Header | `Authorization: Bearer <TOKENHUB_API_KEY>` |

建议把 API Key 配置为本地环境变量，避免写进截图、配置文件或公开仓库：

```bash
export TOKENHUB_API_KEY="your-tokenhub-api-key"
```

Windows PowerShell:

```powershell
$env:TOKENHUB_API_KEY="your-tokenhub-api-key"
```

## 工具指南

| 工具 | 类型 | 指南 |
| --- | --- | --- |
| OpenRouter-compatible API workflow | 聚合网页平台 / API 工作流 | [openrouter-compatible.md](./openrouter-compatible.md) |
| Cursor | AI IDE | [cursor.md](./cursor.md) |
| CodeBuddy / WorkBuddy | AI 工具 | [codebuddy-workbuddy.md](./codebuddy-workbuddy.md) |
| Continue | VS Code 插件 | [continue.md](./continue.md) |
| Cline | VS Code 插件 | [cline.md](./cline.md) |
| Roo Code | VS Code 插件 | [roo-code.md](./roo-code.md) |
| Dify | 低代码 / Agent 平台 | [dify.md](./dify.md) |

## 小作品 Demo

示例小作品选择 Dify + Hy3，构建一个“需求澄清助手”，用于把一句模糊需求转成可执行的开发任务卡片。

- Demo 文档：[showcase-requirement-assistant.md](./showcase-requirement-assistant.md)
- 示例图：[assets/showcase-requirement-assistant.svg](./assets/showcase-requirement-assistant.svg)

## 使用建议

- 第一次接入时先做一个最小对话请求，确认 API Key、Base URL 和模型名无误。
- 如果工具中有 “OpenAI Compatible”、“Custom OpenAI”、“OpenAI API Compatible” 等选项，优先选择这些模式。
- 如果工具要求填写完整 endpoint，使用 `https://tokenhub.tencentmaas.com/v1/chat/completions`；如果只要求 Base URL，使用 `https://tokenhub.tencentmaas.com/v1`。
- 如果工具默认自动追加 `/v1`，不要重复填写 `/v1/v1`。
- 如果出现 401，优先检查 API Key 是否来自 TokenHub，以及是否错误添加了 `Bearer ` 前缀。
- 如果出现 429，说明触发限流或配额限制，应降低并发或稍后重试。
