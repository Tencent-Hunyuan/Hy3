# 01 · Basic Chat(单轮 / 多轮)

最基础的 `chat.completions` 调用。可运行脚本:`01_basic_chat.py`。

---

## 单轮

### 请求(curl)

```bash
curl -X POST 'https://tokenhub.tencentmaas.com/v1/chat/completions' \
  -H 'Authorization: Bearer $HY3_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "hy3",
    "messages": [{"role": "user", "content": "用一句话解释什么是向量数据库"}],
    "temperature": 0.7,
    "max_tokens": 200
  }'
```

### 请求(Python)

```python
resp = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "用一句话解释什么是向量数据库"}],
    temperature=0.7,
    max_tokens=200,
)
print(resp.choices[0].message.content)
```

### 真实响应(节选)

```json
{
  "model": "hy3",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "向量数据库是一种专门存储和检索高维向量数据的系统……"
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 14, "completion_tokens": 48, "total_tokens": 62,
    "completion_tokens_details": { "reasoning_tokens": 0 }
  }
}
```

---

## 多轮(带 system + 历史)

把完整对话历史放进 `messages`,Hy3 会结合上下文回答。

### 请求

```python
resp = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "system", "content": "你是健身教练, 回答简洁"},
        {"role": "user", "content": "增肌每天该吃多少蛋白质?"},
        {"role": "assistant", "content": "一般建议每公斤体重 1.6~2.2 克。"},
        {"role": "user", "content": "那 70 公斤的人大概多少克?"},
    ],
    temperature=0.5,
    max_tokens=200,
)
```

### 真实响应

```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "70公斤约需112~154克蛋白质/天。"
    },
    "finish_reason": "stop"
  }],
  "usage": { "prompt_tokens": 55, "completion_tokens": 13, "total_tokens": 68 }
}
```

模型正确理解了「70 公斤」这个上下文,并基于上一轮的「1.6~2.2 g/kg」算出 112~154 克。

---

## response 解析要点

- **content**:`choices[0].message.content`
- **为何停**:`choices[0].finish_reason` —— `stop`(自然结束)/ `length`(被 `max_tokens` 截断)/ `tool_calls`(要调工具)
- **token 用量**:`usage.{prompt_tokens, completion_tokens, total_tokens}`
