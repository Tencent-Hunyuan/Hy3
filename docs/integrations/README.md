# Hy3 主流工具接入指南

> 面向终端用户：在常用 AI 产品里把 **Hy3** 用起来。  
> 对应犀牛鸟 Issue [#2](https://github.com/Tencent-Hunyuan/Hy3/issues/2)。

本目录提供 **配置 → 第一次对话 → 真实任务** 的实战流程。后端可选：

| 后端 | Base URL | Model | API Key |
|------|----------|-------|---------|
| [TokenHub](https://cloud.tencent.com/document/product/1823/132252) | `https://tokenhub.tencentmaas.com/v1` | `hy3` | TokenHub Key |
| [OpenRouter](https://openrouter.ai/tencent/hy3) | `https://openrouter.ai/api/v1` | `tencent/hy3` | `sk-or-...` |

> Cursor 走 OpenRouter 时，Base URL 常需使用专用地址 `https://openrouter.ai/api/v1/cursor`（见 [Cursor 指南](./cursor.md)）。

## 工具索引

| # | 工具 | 类型 | 指南 |
|---|------|------|------|
| 1 | OpenRouter | 聚合 API / 网页 | [openrouter.md](./openrouter.md) |
| 2 | Cursor | AI IDE | [cursor.md](./cursor.md) |
| 3 | Continue | VS Code / JetBrains 插件 | [continue.md](./continue.md) |
| 4 | Codex CLI | 终端 Agent | [codex-cli.md](./codex-cli.md) |
| 5 | Dify | 低代码 / Agent 平台 | [dify.md](./dify.md) |

## 小作品（Part B）

独立开源应用：**Hy3 Workbench**（网页 Agent 工作台，支持思考模式 + 工具调用）

- 仓库：<https://github.com/xianggkl/hy3-showcase>（推送后更新为你的实际地址）
- 能力：推理（`thinking` / `reasoning_effort`）、Function Calling、多轮工具回填
- 本地启动见该仓库 README；演示 GIF/视频放在仓库 `docs/demo.gif`

## 建议阅读顺序

1. [OpenRouter](./openrouter.md) — 先拿到一把通用 Key  
2. [Cursor](./cursor.md) — IDE 里写代码  
3. [Continue](./continue.md) — VS Code 轻量接入  
4. [Codex CLI](./codex-cli.md) — 终端 Agent  
5. [Dify](./dify.md) — 无代码搭 Agent  

## 截图说明

各指南 `assets/` 下的示意图用于说明配置路径；**请用你本机真实配置界面截图替换** `docs/integrations/assets/*-screenshot.png` 占位说明（见各文档「截图清单」），再提交 PR。
