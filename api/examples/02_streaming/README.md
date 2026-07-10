# 02 - Streaming（流式输出）

演示如何使用 SSE 流式请求，并逐 chunk 解析响应。

## 说明

流式模式下，模型在生成过程中逐 token 推送数据，用户可以在完整响应到达前看到部分结果，显著降低首 token 感知延迟。

## 运行方式

```bash
pip install openai python-dotenv
cp ../../.env.example ../../.env  # 编辑 .env 填入密钥
python streaming.py
```

## 代码

```python
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("HY3_API_KEY", "EMPTY"),
    base_url=os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
)

stream = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "请写一段 200 字左右的短文，主题是人工智能的未来。"},
    ],
    stream=True,
    temperature=0.9,
    top_p=1.0,
)

full_content = ""
for chunk in stream:
    delta = chunk.choices[0].delta
    if delta.content:
        content = delta.content
        full_content += content
        print(content, end="", flush=True)

print(f"\n\n--- Stream 结束 ---")
```

### Chunk 结构

典型 chunk 格式（非最后一个）：

```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion.chunk",
  "created": 1719000000,
  "model": "hy3",
  "choices": [
    {
      "index": 0,
      "delta": {"role": "assistant", "content": "人工"},
      "finish_reason": null
    }
  ]
}
```

最后一个 chunk：

```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion.chunk",
  "created": 1719000000,
  "model": "hy3",
  "choices": [
    {
      "index": 0,
      "delta": {},
      "finish_reason": "stop"
    }
  ]
}
```

### 获取 usage 信息

设置 `stream_options={"include_usage": True}`，最后一个 chunk 会包含 usage 字段：

```python
stream = client.chat.completions.create(
    model="hy3",
    messages=[...],
    stream=True,
    stream_options={"include_usage": True},
)
```

---

完整源码：[streaming.py](./streaming.py)
