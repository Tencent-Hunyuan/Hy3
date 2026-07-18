# OpenRouter × Hy3

在 [OpenRouter](https://openrouter.ai) 上选用腾讯 Hy3，一套 Key 可给 Cursor、Continue、Codex CLI 等多款工具复用。

## 本目录文件

| 文件 | 用途 |
|------|------|
| [`.env.example`](./.env.example) | （可选）本地覆盖；推荐改用上级统一 `.env` + `../sync_env.sh` |
| [`curl_chat.sh`](./curl_chat.sh) | 一键 curl 最小对话 |
| [`chat_example.py`](./chat_example.py) | Python OpenAI SDK 示例 |
| [`requirements.txt`](./requirements.txt) | Python 依赖 |

```bash
cd docs/integrations
cp .env.example .env && $EDITOR .env
./sync_env.sh
bash openrouter/curl_chat.sh
```

## 安装与版本

| 项 | 要求 |
|----|------|
| 账号 | [openrouter.ai](https://openrouter.ai) 注册 |
| API | OpenAI 兼容；SDK 建议 `openai >= 1.40` |
| 模型页 | [tencent/hy3](https://openrouter.ai/tencent/hy3) |

## 配置项

| 配置 | 值 |
|------|-----|
| Base URL | `https://openrouter.ai/api/v1` |
| Model | `tencent/hy3` |
| Auth | `Authorization: Bearer sk-or-...` |
| 协议 | OpenAI Chat Completions |

也可在 OpenRouter 网页 Chat 中直接选择 **Tencent: Hy3**。

## 端到端任务 Demo

让 Hy3 实现 `top_k_frequent` 并附 3 行复杂度说明；截图存 `../assets/openrouter-chat-demo.png`。

## 注意事项

- Key 前缀 `sk-or-`；模型名必须是 `tencent/hy3`。
- 只提交 `.env.example`，不要提交真实 `.env`。

## 截图清单

| 文件 | 内容 |
|------|------|
| `../assets/openrouter-models.png` | 模型页选中 Hy3 |
| `../assets/openrouter-chat-demo.png` | 编码任务对话 |
