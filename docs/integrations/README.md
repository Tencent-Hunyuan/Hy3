# Hy3 集成指南

在主流 AI 产品中使用腾讯混元 Hy3 模型的实战配置指南。本目录面向终端用户，每个指南均包含：安装与版本要求 → 核心配置 → 第一次对话测试 → 端到端实战 Demo → 常见注意事项。

## 工具清单

| 类别 | 工具 | 指南 | 类型 |
|------|------|------|------|
| AI IDE | [Cursor](./cursor.md) | AI 原生编辑器 | 桌面应用 |
| VS Code 插件 | [Cline](./cline.md) | AI 编程助手 | VS Code 插件 |
| VS Code 插件 | [Roo Code](./roo-code.md) | AI 编程助手 | VS Code 插件 |
| VS Code 插件 | [Continue](./continue.md) | 开源 AI 编程助手 | VS Code / JetBrains |
| Agent CLI | [Codex CLI](./codex-cli.md) | AI 编程 Agent CLI | 终端 |
| Agent CLI | [Aider](./aider.md) | AI 结对编程 CLI | 终端 |

## 通用配置

Hy3 提供 OpenAI Compatible 接口，协议统一，仅 Base URL / 模型名 / API Key 因服务商而异：

| 部署模式 | Base URL | 模型名 | API Key |
|----------|----------|--------|---------|
| **TokenHub（国内）** | `https://tokenhub.tencentmaas.com/v1` | `hy3` | TokenHub Key |
| **TokenHub（海外）** | `https://tokenhub-intl.tencentmaas.com/v1` | `hy3` | TokenHub Key |
| **OpenRouter** | `https://openrouter.ai/api/v1` | `tencent/hy3` | OpenRouter Key |
| **本地部署** | `http://127.0.0.1:8000/v1` | `hy3` | `EMPTY` |

> **区域选择**：TokenHub 使用区域专属域名，必须与 API Key 创建区域一致。

## 推理模式

通过 `chat_template_kwargs.reasoning_effort` 控制快慢双模式：

| 模式 | 值 | 说明 | 适用场景 |
|------|-----|------|---------|
| 直接回复 | `no_think` | 快速响应，无推理过程 | 翻译、简单问答 |
| 轻度推理 | `low` | 平衡模式，有简短推理 | 代码生成、文档分析 |
| 深度推理 | `high` | 完整深度思考链 | 数学证明、复杂逻辑、代码审查 |

## 演示项目

[Hy3 Code Reviewer](./showcase/) 是一个基于 Hy3 推理能力的 CLI 代码审查工具：

- **核心能力**：深度推理 + 代码分析
- **使用方式**：CLI 命令行工具
- **功能**：审查任意代码文件，输出结构化审查意见

## 使用建议

1. **先通后精**：第一次接入时先做最小对话测试，确认 API Key、Base URL 和模型名无误
2. **协议选择**：优先选择 "OpenAI Compatible"、"Custom OpenAI" 等模式
3. **Base URL**：注意工具是否自动追加 `/v1`，避免重复
4. **模型名**：与服务商对齐（本地 `hy3` / OpenRouter `tencent/hy3` / TokenHub `hy3`）
5. **流式输出**：大部分工具默认开启 `stream`，关闭后长回复可能超时
6. **Troubleshooting**：
   - 401 → 检查 API Key 和是否多写 `Bearer` 前缀
   - 404 → 检查 Base URL 是否多/少 `/v1`
   - 429 → 触发限流，降低并发或稍后重试
