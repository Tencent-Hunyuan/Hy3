# Hy3 集成指南

在主流 AI 产品中使用 Tencent Hy3 模型的实战配置指南。本目录面向终端用户，每个指南均包含：安装与版本要求 → 核心配置 → 第一次对话测试 → 端到端实战 Demo → 常见注意事项。

## 工具清单

| 类别 | 工具 | 指南 | 类型 |
|------|------|------|------|
| 聚合 API | [OpenRouter](./openrouter.md) | 统一 API 网关 | API 代理 |
| AI IDE 插件 | [WorkBuddy](./workbuddy.md) | AI 辅助开发 | VS Code / JetBrains |
| AI IDE 插件 | [CodeBuddy](./codebuddy.md) | AI 编程助手 | VS Code / JetBrains |
| Agent CLI | [Claude Code](./claude-code.md) | AI 编程 Agent CLI | 终端 |
| 低代码平台 | [Dify](./dify.md) | 可视化 AI 应用搭建 | Web / Docker |

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

## 与其他贡献的关系

社区中多位同学已贡献了不同工具的接入方案，本指南与以下 PR 为互补关系：

| PR | 贡献者 | 覆盖工具 | 亮点 |
|----|--------|----------|------|
| [#19](https://github.com/Tencent-Hunyuan/Hy3/pull/19) | tlyssd | OpenRouter, Cursor, CodeBuddy, WorkBuddy, Cline, Roo Code, Dify | Dify 需求助手小作品 |
| [#33](https://github.com/Tencent-Hunyuan/Hy3/pull/33) | dredgeship | CLine, CodeBuddy IDE, OpenRouter, Roo Code, ClaudeCode | 产品能力总览展示 |
| [#37](https://github.com/Tencent-Hunyuan/Hy3/pull/37) | xy200303 | Codex CLI, Aider, Claude Code, Continue, Open WebUI | Vibemotion 科普动画小作品 |
| 本 PR | lazypool | OpenRouter, CodeBuddy, WorkBuddy, Claude Code, Dify | 知识图谱小作品 + SVG 流程图解 |

## 演示项目

[Hy3 Showcase](https://github.com/lazypool/hy3-showcase) 是一个基于 Hy3 的交互式知识图谱展示应用：

- **核心能力**：推理 + 工具调用 + 知识图谱构建
- **双界面**：CLI + Web（Streamlit）
- **Mock/真实 API 自动切换**：无需 Key 即可体验
- **19 项自动化测试**：覆盖推理、工具调用、图谱构建等

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
