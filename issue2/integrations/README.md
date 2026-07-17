# Hy3 主流 AI 工具集成实战指南 · 索引

> 🌐 English version: [README.en.md](README.en.md)

## 概述

本文档集合面向**终端用户**，介绍如何在 5 个主流 AI 平台 / 客户端工具中集成 **腾讯混元 Hy3**（295B MoE 模型，OpenAI 兼容 API），让开发者、创作者无需自建服务即可在常用工作流中调用 Hy3 的推理、Agent 与长上下文能力。

> **Hy3 核心能力速览**
> - **推理模式**：`reasoning_effort` 支持 `no_think`（直接回复）/ `low` / `high`（深度思维链）
> - **Agent/工具调用**：原生支持 Function Call，适配 vLLM `hy_v3` parser
> - **上下文窗口**：最大 256K tokens
> - **推荐参数**：`temperature=0.9`, `top_p=1.0`（官方推荐）

## 覆盖工具

| # | 工具 | 类型 | 适用场景 | 指南 |
|:---:|:---|:---|:---|:---:|
| 1 | **OpenRouter** | 聚合 API 网关 | 零部署、多模型对比、统一计费 | [→](openrouter/openrouter.md) |
| 2 | **Cursor** | AI IDE | 编程、代码补全、项目级 Agent | [→](cursor/cursor.md) |
| 3 | **CodeBuddy / WorkBuddy** | AI 开发助手 | 全栈项目生成、工作流自动化 | [→](codebuddy/codebuddy.md) |
| 4 | **Codex CLI** | 终端 AI 编程 | 命令行编码、自动化脚本 | [→](codex-cli/codex-cli.md) |
| 5 | **Dify** | 低代码 Agent 平台 | 可视化 Agent 编排、知识库 RAG | [→](dify/dify.md) |

## 快速选择

- **想最快的体验 Hy3？** → [OpenRouter](openrouter/openrouter.md)
- **要在 IDE 里用 Hy3 写代码？** → [Cursor](cursor/cursor.md)
- **想构建全栈项目？** → [CodeBuddy](codebuddy/codebuddy.md) / [Codex CLI](codex-cli/codex-cli.md)
- **想搭建 Agent 工作流？** → [Dify](dify/dify.md)

## 前置条件

所有工具共用一个前置：**一个可访问的 Hy3 OpenAI 兼容端点**。你可以：

1. **自建服务**（推荐）：按 [Hy3 README](../../README.md) 用 vLLM/SGLang 部署
2. **使用 API 代理**：通过 OpenRouter 等聚合平台调用（无需 GPU）
3. **云服务**：腾讯云 AI Studio 等官方渠道

> 💡 本文档中的所有示例均假设 `base_url` = `http://127.0.0.1:8000/v1`，`model` = `hy3`。
> 如使用 OpenRouter 等代理，请替换为对应的 base_url 和 model ID。
