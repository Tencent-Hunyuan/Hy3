# Cursor × Hy3

在 [Cursor](https://cursor.com) 中通过自定义 OpenAI 兼容接口使用 Hy3。  
**配置对照文件路径均相对于仓库根目录 `Hy3/`。**

## 本目录文件

| 文件 | 用途 |
|------|------|
| [`docs/integrations/cursor/settings.openrouter.example.json`](./settings.openrouter.example.json) | OpenRouter 配置对照 |
| [`docs/integrations/cursor/settings.tokenhub.example.json`](./settings.tokenhub.example.json) | TokenHub 直连对照 |

> 在 Cursor **Settings UI** 按 JSON 字段填写；勿提交真实 Key。

统一密钥（可选，供脚本读取）：

```bash
cp docs/integrations/.env.example docs/integrations/.env
bash docs/integrations/sync_env.sh
# 生成 docs/integrations/cursor/.env
```

## 安装与版本

最新稳定版 Cursor；Key 用 OpenRouter 或 TokenHub。

## 配置项

### OpenRouter（推荐）

对照 `docs/integrations/cursor/settings.openrouter.example.json`：

1. Settings → Models  
2. OpenAI API Key = OpenRouter Key  
3. Override Base URL：`https://openrouter.ai/api/v1/cursor`  
4. Add model：`tencent/hy3`

### TokenHub

对照 `docs/integrations/cursor/settings.tokenhub.example.json`：  
Base URL：`https://tokenhub.tencentmaas.com/v1`，Model：`hy3`。

## 第一次对话

Chat 中选 Hy3，发送：`用三句话说明你适合做什么。`  
截图：`docs/integrations/assets/cursor-first-chat.png`

## 端到端任务 Demo

Agent：新增 `greet` 函数 + unittest。GIF：`docs/integrations/assets/cursor-agent-demo.gif`

## 注意事项

- OpenRouter 必须用 `/v1/cursor`。
- OpenRouter 模型名 `tencent/hy3`；TokenHub 为 `hy3`。

## 截图清单

| 文件 | 内容 |
|------|------|
| `docs/integrations/assets/cursor-settings.png` | 配置页 |
| `docs/integrations/assets/cursor-first-chat.png` | 第一次对话 |
| `docs/integrations/assets/cursor-agent-demo.gif` | Agent 任务 |
