# 截图指南

以下列出每个工具需要截取的截图位置和内容。截图放入各工具对应的目录（`screenshots/<tool>/`）。

---

## 1. OpenRouter

| # | 截图内容 | 操作步骤 |
|---|---------|---------|
| 1 | Hy3 模型详情页 | 打开 https://openrouter.ai/models/tencent/hy3，截图包含模型信息、定价 |
| 2 | 模型选择 + Quick Start 代码 | 同上页面，滚动到 Quick Start 区域 |

## 2. Cursor

| # | 截图内容 | 操作步骤 |
|---|---------|---------|
| 1 | Cursor Settings → Models 页面 | 打开 Cursor → Settings → Models，添加 Hy3 配置 |
| 2 | Chat 对话 | 在 Cursor 中 Ctrl+L 打开 Chat，发送一条消息 |

## 3. Cline (VS Code)

| # | 截图内容 | 操作步骤 |
|---|---------|---------|
| 1 | Cline 配置弹窗 | VS Code → 点击侧边栏 Cline 图标 → 顶部的 API Provider 下拉选择 "OpenAI Compatible" → 填入 Hy3 参数 |
| 2 | Cline 对话 | 在 Cline Chat 中输入 "介绍一下你自己" |

**已配置：** VS Code settings 中已写入：
```json
cline.apiProvider: "openai"
cline.openAiBaseUrl: "http://127.0.0.1:8000/v1"
cline.openAiApiKey: "EMPTY"
cline.openAiModelId: "hy3"
```

## 4. Continue (VS Code)

| # | 截图内容 | 操作步骤 |
|---|---------|---------|
| 1 | Continue 配置页面 | VS Code → 点击侧边栏 Continue → 齿轮图标 → 确认模型列表中有 Hy3 |
| 2 | Continue 对话 | 在 Continue Chat 中提问 |

**已配置：** `~/.continue/config.json` 已写入 Hy3 配置。

## 5. Roo Code (VS Code)

| # | 截图内容 | 操作步骤 |
|---|---------|---------|
| 1 | Roo Code 配置 | VS Code → 点击侧边栏 Roo Code → API Provider 选择 OpenAI Compatible → 填入 Hy3 |
| 2 | Roo Code 对话 | 发送一条消息验证 |

## 6. Aider (终端)

| # | 截图内容 | 操作步骤 |
|---|---------|---------|
| 1 | Aider 启动 | 终端运行 `aider --model openai/hy3 --openai-api-base http://127.0.0.1:8000/v1 --openai-api-key EMPTY` |
| 2 | Aider 对话 | 启动后输入一个编程问题 |

**已配置：** `~/.aider.conf.yml` 已写入 Hy3 配置。

## 7. Dify

| # | 截图内容 | 操作步骤 |
|---|---------|---------|
| 1 | Dify 模型配置页 | 登录 dify.ai → 设置 → 模型供应商 → OpenAI-API-compatible → 填入 Hy3 参数 |
| 2 | Dify Agent 应用 | 创建 Agent 应用 → 选择 hy3 模型 → 运行 |

## 8. Showcase App (hy3-showcase)

Hy3 Playground — Flask Web 应用，演示推理 / 工具调用 / 流式输出三大能力。

| # | 截图内容 | 操作步骤 |
|---|---------|---------|
| 1 | 推理模式对比 | `python app.py` → 打开浏览器 → 点击"三档模式对比" |
| 2 | 工具调用链路 | 切换到"工具调用" → 点击"运行 Agent"，截图调用日志 |
| 3 | 流式输出 | 切换到"流式对话" → 点击"开始流式输出" |
| 4 | 流式输出 Tab | 输入问题 → 点击"开始流式输出" |
