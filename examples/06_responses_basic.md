# 06 Responses API basic call

Run a minimal Responses API request.

```bash
uv run --env-file .env python examples/06_responses_basic.py
```

The script calls `client.responses.create()` and reads the final text from `response.output_text`. Applications that need tools or reasoning should also inspect `response.output`.

## Output example

```text
我是混元，是由腾讯开发的大模型。我专注于基础信息处理与逻辑响应，支持多模态输入（文本、图片、文件等）……
```

English translation: “I am Hunyuan, a large model developed by Tencent. I focus on information processing and logical responses, and support multimodal inputs such as text, images, and files.”
