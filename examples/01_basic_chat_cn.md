# 01 基础对话

使用 Chat Completions API 完成一次最小文本调用。

## 运行

```bash
uv run --env-file .env python examples/01_basic_chat.py
```

## 请求和解析

脚本通过 `client.chat.completions.create()` 发送 `model`、`messages` 和 `stream: false`，并从 `response.choices[0].message.content` 读取模型回复。

## 输出示例

```text
你好！我是你的智能助手，可以帮你解答各类问题、提供信息查询、协助写作、整理资料、聊天交流等。无论是学习、工作还是生活里的小疑问，都可以随时跟我说～ 你有什么需要帮忙的吗？
```

具体措辞会因模型版本和采样结果变化。
