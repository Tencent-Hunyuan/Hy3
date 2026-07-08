# Hy3 Integrations

将 Hy3 接入主流 AI 产品和工具的使用指南（Issue #2 · Part A）。

每个指南包含：安装与版本要求、配置项、端到端流程（配置 → 第一次对话 → 跑通真实任务）、端到端 demo 截图、常见注意事项。

## 工具列表（8 个，覆盖 issue 建议的全部类别）

| 类别 | 工具 | 指南 | 已本地安装验证 |
|------|------|------|----------------|
| 聚合 API 平台 | OpenRouter | [openrouter.md](./openrouter.md) | ✅ 模型已上架 |
| AI IDE | Cursor | [cursor.md](./cursor.md) | — |
| AI 编程助手 | CodeBuddy | [codebuddy.md](./codebuddy.md) | — |
| CLI 编程工具 | Aider | [aider.md](./aider.md) | ✅ v0.86.2 |
| VS Code 插件 | Cline | [cline.md](./cline.md) | ✅ v4.0.6 |
| VS Code 插件 | Continue | [continue.md](./continue.md) | ✅ v2.0.0 |
| VS Code 插件 | Roo Code | [roo-code.md](./roo-code.md) | ✅ v3.54.0 |
| 低代码/Agent 平台 | Dify | [dify.md](./dify.md) | — |

## 前提

所有指南假设 Hy3 已部署并可访问。参考 [Deployment](https://github.com/Tencent-Hunyuan/Hy3?tab=readme-ov-file#deployment)。

| 部署方式 | 默认 Base URL | 默认 Model 名 |
|----------|---------------|---------------|
| vLLM | `http://127.0.0.1:8000/v1` | `hy3` |
| SGLang | `http://127.0.0.1:8000/v1` | `hy3` |
| OpenRouter（云端） | `https://openrouter.ai/api/v1` | `tencent/hy3` |

## Part B

基于 Hy3 的小作品见独立分支 [`hy3-showcase`](https://github.com/Piggy343288/Hy3/tree/hy3-showcase)：Hy3 Playground（Flask Web 应用，演示推理 / 工具调用 / 流式输出）。

## 截图 / GIF

各工具端到端 demo 截图存放与拍摄说明见 [../../screenshots/README.md](../../screenshots/README.md)。
