# 01 Basic chat

Run a minimal Chat Completions request.

```bash
uv run --env-file .env python examples/01_basic_chat.py
```

The script sends `model`, `messages`, and `stream: false`, then reads `response.choices[0].message.content`.

## Output example

Observed output from one run:

```text
你好！我是你的智能助手，可以帮你解答各类问题、提供信息查询、协助写作、整理资料、聊天交流等。无论是学习、工作还是生活里的小疑问，都可以随时跟我说～ 你有什么需要帮忙的吗？
```

English translation: “Hello! I am your intelligent assistant. I can answer questions, provide information, help with writing and organizing materials, and chat with you.”

Output wording may vary by model version and sampling.
