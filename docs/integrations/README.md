# 在主流 AI 工具中使用腾讯混元 Hy3

本目录收录了腾讯混元 Hy3 大模型在 6 款主流 AI 工具/平台中的接入与使用指南。每份指南均同时提供 **OpenRouter**（国际通用，免费至 2026-07-21）和 **腾讯云 TokenHub**（国内推荐）两种接入方式。

## 为什么选择 Hy3

Hy3 是腾讯混元团队研发的 295B 参数 MoE 大模型（激活 21B），支持 256K 上下文，核心优势包括：

- **强推理能力**：支持 `no_think` / `low` / `high` 三档推理模式，GPQA Diamond 达 90.4
- **可靠 Agent**：工具调用跨脚手架泛化性方差 <4%
- **抗幻觉**：幻觉率从 12.5% 降至 5.4%
- **高性价比**：OpenRouter $0.14/$0.58 per 1M tokens，TokenHub ¥1/¥4 per M tokens

## 通用配置速查表

| 配置项 | OpenRouter | 腾讯云 TokenHub | 本地部署 (vLLM/SGLang) |
|--------|-----------|----------------|----------------------|
| **Base URL** | `https://openrouter.ai/api/v1` | `https://tokenhub.tencentmaas.com/v1` | `http://127.0.0.1:8000/v1` |
| **Model 名称** | `tencent/hy3` | `hy3` | `hy3` |
| **API Key 获取** | [openrouter.ai/keys](https://openrouter.ai/keys) | [TokenHub 控制台](https://console.cloud.tencent.com/tokenhub) | 本地无需鉴权 |
| **免费额度** | 截止 2026-07-21（`tencent/hy3:free`） | 新人 100 万 Tokens（90天） | 自建成本 |
| **输入价格** | $0.14 / 1M tokens | ¥1 / M tokens | 自建成本 |
| **输出价格** | $0.58 / 1M tokens | ¥4 / M tokens | 自建成本 |
| **缓存命中** | 自动 | ¥0.25 / M tokens | — |
| **协议兼容** | OpenAI Chat Completions API | OpenAI Chat Completions API | OpenAI Chat Completions API |
| **推理模式** | `reasoning` 参数 | `reasoning_effort` 参数 | `chat_template_kwargs` |

## 接入工具列表

| 序号 | 工具 | 类型 | 指南 | 适用场景 |
|------|------|------|------|---------|
| 1 | **OpenRouter** | 聚合 API 平台 | [openrouter.md](./openrouter.md) | 零门槛入门，快速体验 |
| 2 | **CodeBuddy / WorkBuddy** | 桌面 AI 智能体 | [codebuddy-workbuddy.md](./codebuddy-workbuddy.md) | 日常 AI 编程与办公 |
| 3 | **Aider** | CLI AI 编程 | [aider.md](./aider.md) | 命令行结对编程 |
| 4 | **Cursor** | AI IDE | [cursor.md](./cursor.md) | IDE 内 AI 辅助开发 |
| 5 | **Cline** | VS Code 插件 | [cline.md](./cline.md) | 轻量级 Agent 编程 |
| 6 | **Dify** | 低代码 Agent 平台 | [dify.md](./dify.md) | 工作流编排与知识库 RAG |

## Hy3 核心能力速览

### 推理模式（Reasoning Effort）

Hy3 支持三种推理强度，通过 `reasoning_effort` 或 `reasoning` 参数控制：

| 模式 | 参数值 | 适用场景 | 响应速度 |
|------|--------|---------|---------|
| 不思考 | `no_think` 或不传 | 日常对话、简单问答 | 最快 |
| 轻度推理 | `low` | 代码审查、概念解释 | 中等 |
| 深度推理 | `high` | 复杂数学、多步推理、架构设计 | 较慢 |

### Agent / 工具调用

Hy3 原生支持 OpenAI 兼容的 Function Calling，可通过 `tool_choice` 参数控制：
- 自动选择：`tool_choice: "auto"`
- 指定工具：`tool_choice: {"type": "function", "function": {"name": "xxx"}}`
- 强制使用：`tool_choice: "required"`

### 长上下文（256K）

256K tokens 上下文窗口，适合长文档分析、多轮对话、代码仓库理解等场景。

## 通用使用建议

1. **新手入门**：先通过 OpenRouter 指南了解 API 调用方式，再迁移到具体工具
2. **免费首选**：OpenRouter 免费至 2026-07-21，零门槛；TokenHub 新人 100 万 Token 适合长期使用
3. **网络选择**：国内用户优先使用 TokenHub，延迟更低；国际用户使用 OpenRouter
4. **推理模式**：简单任务用 `no_think` 省 Token，复杂任务用 `high` 获得更好结果
5. **Agent 场景**：确保启用了工具调用支持，Hy3 在 Agent 场景下表现显著优于预览版
6. **错误排查**：首选用 curl 测试端点连通性，确认 API Key 有效后再配置工具
