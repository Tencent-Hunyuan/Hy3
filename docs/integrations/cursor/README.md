# Cursor × Hy3

在 [Cursor](https://cursor.com) 中通过自定义 OpenAI 兼容接口使用 Hy3。

## 本目录文件

| 文件 | 用途 |
|------|------|
| [`settings.openrouter.example.json`](./settings.openrouter.example.json) | OpenRouter 配置对照 |
| [`settings.tokenhub.example.json`](./settings.tokenhub.example.json) | TokenHub 直连对照 |

> 在 Cursor **Settings UI** 按 JSON 字段填写；勿提交真实 Key。

## 安装与版本

最新稳定版 Cursor；Key 用 OpenRouter 或 TokenHub。

## 配置项

### OpenRouter（推荐）

1. Settings → Models  
2. OpenAI API Key = OpenRouter Key  
3. Override Base URL：

```text
https://openrouter.ai/api/v1/cursor
```

4. Add model：`tencent/hy3`

### TokenHub

Base URL：`https://tokenhub.tencentmaas.com/v1`，Model：`hy3`。详见 `settings.tokenhub.example.json`。

## 第一次对话

Chat 中选 Hy3，发送：`用三句话说明你适合做什么。`  
截图：`../assets/cursor-first-chat.png`

## 端到端任务 Demo

Agent：新增 `greet` 函数 + unittest。GIF：`../assets/cursor-agent-demo.gif`

## 注意事项

- OpenRouter 必须用 `/v1/cursor`。
- OpenRouter 模型名 `tencent/hy3`；TokenHub 为 `hy3`。

## 截图清单

| 文件 | 内容 |
|------|------|
| `../assets/cursor-settings.png` | 配置页 |
| `../assets/cursor-first-chat.png` | 第一次对话 |
| `../assets/cursor-agent-demo.gif` | Agent 任务 |
