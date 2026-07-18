# 02 · Streaming(流式请求 + 逐 chunk 解析)

`stream: true` 开启 SSE 流式输出,适合实时展示生成过程(聊天打字机、长文边生成边读)。可运行脚本:`02_streaming.py`。

---

## 请求

```bash
curl -N -X POST 'https://tokenhub.tencentmaas.com/v1/chat/completions' \
  -H 'Authorization: Bearer $HY3_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "hy3",
    "messages": [{"role": "user", "content": "写一句关于编程的话"}],
    "stream": true,
    "max_tokens": 80
  }'
```

```python
stream = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "写一句关于编程的话"}],
    stream=True,
    max_tokens=80,
)
for chunk in stream:
    delta = chunk.choices[0].delta
    reasoning = getattr(delta, "reasoning_content", None)   # 思考内容(如有)
    if reasoning:
        print(f"[think] {reasoning}", end="", flush=True)
    if delta.content:
        print(delta.content, end="", flush=True)
```

---

## 真实响应(SSE 原始 chunk)

每个 `data:` 是一个 chunk,`delta.content` 是增量片段,拼接即完整文本:

```
data: {"id":"340a29d6-...","object":"chat.completion.chunk","model":"hy3","choices":[{"index":0,"delta":{"role":"assistant"}}]}

data: {...,"choices":[{"index":0,"delta":{"content":"编程"}}]}

data: {...,"choices":[{"index":0,"delta":{"content":"不是"}}]}

data: {...,"choices":[{"index":0,"delta":{"content":"让"}}]}

data: {...,"choices":[{"index":0,"delta":{"content":"计算机"}}]}

data: {...,"choices":[{"index":0,"delta":{"content":"理解"}}]}

data: {...,"choices":[{"index":0,"delta":{"content":"人，"}}]}

data: {...,"choices":[{"index":0,"delta":{"content":"而是让人"}}]}

data: [DONE]
```

**拼接结果**:`编程不是让计算机理解人，而是让人……`

---

## chunk 解析要点

- **首 chunk**:`delta.role = "assistant"`,`content` 通常为空
- **正文 chunk**:`delta.content` 为增量文本(注意是**增量**,需自行累加)
- **思考 chunk**(推理时):`delta.reasoning_content` —— 增量思考片段,与正文分开
- **结束**:`data: [DONE]`
- 每个 chunk 的 `object` 是 `chat.completion.chunk`(区别于非流式的 `chat.completion`)

> 流式下 TTFT(首 token 时延)显著低于非流式,详见 [example 03](03_streaming_vs_nonstream.md)。
