# Hy3 Integrations

将 Hy3 接入主流 AI 产品和工具的使用指南。

## 工具列表

| 工具 | 类型 | 难度 | 说明 |
|------|------|------|------|
| [OpenRouter](./openrouter.md) | API 聚合平台 | ★☆☆ | 通过 OpenRouter 直接调用 Hy3 API |
| [Cursor](./cursor.md) | AI IDE | ★☆☆ | 在 Cursor 中配置并使用 Hy3 |
| [Cline](./cline.md) | VS Code 插件 | ★☆☆ | VS Code 中通过 Cline 使用 Hy3 |
| [Dify](./dify.md) | 低代码 AI 平台 | ★★☆ | 在 Dify 中配置 Hy3 作为 LLM 节点 |
| [Aider](./aider.md) | CLI 编程工具 | ★★☆ | 终端中使用 Aider + Hy3 进行 AI 编程 |
| [CodeBuddy](./codebuddy.md) | AI 编程助手 | ★★☆ | 在 CodeBuddy 中使用 Hy3 |

## 前提

所有指南均假设 Hy3 已部署并可访问（本地或云端），参考 [Deployment](https://github.com/Tencent-Hunyuan/Hy3?tab=readme-ov-file#deployment)。

| 部署方式 | 默认 Base URL | 默认 Model Name |
|----------|---------------|-----------------|
| vLLM | `http://127.0.0.1:8000/v1` | `hy3` |
| SGLang | `http://127.0.0.1:8000/v1` | `hy3` |
| OpenRouter (云端) | `https://openrouter.ai/api/v1` | `tencent/hy3` |
