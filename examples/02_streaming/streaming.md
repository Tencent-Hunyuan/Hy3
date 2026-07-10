# 示例 2：Streaming（流式请求）

## 概述

流式模式（`stream=True`）让模型逐 token 返回内容，而非一次性返回全部结果。适用于：

- **实时对话**：用户能立即看到模型开始回答
- **长文本生成**：不需要等待全部生成完毕
- **首 token 低延迟场景**：对交互响应速度要求高的应用

---

## 请求与响应对比

### 非流式请求

```json
// 请求：一次发送
POST https://tokenhub.tencentmaas.com/v1/chat/completions
{
  "model": "hy3",
  "messages": [{"role": "user", "content": "请写一段短文。"}],
  "stream": false
}

// 响应：一次性返回完整 JSON
{
  "choices": [{"message": {"content": "完整内容..."}, "finish_reason": "stop"}],
  "usage": {...}
}
```

### 流式请求

```json
// 请求：设置 stream=true
POST https://tokenhub.tencentmaas.com/v1/chat/completions
{
  "model": "hy3",
  "messages": [{"role": "user", "content": "请写一段短文。"}],
  "stream": true
}

// 响应：多个 Server-Sent Events，每个 chunk 包含增量内容
data: {"choices":[{"delta":{"content":"人工"},"finish_reason":null}]}
data: {"choices":[{"delta":{"content":"智能"},"finish_reason":null}]}
data: {"choices":[{"delta":{"content":"是"},"finish_reason":null}]}
...
data: {"choices":[{"delta":{},"finish_reason":"stop"}]}
data: [DONE]
```

---

## 流式 chunk 结构解析

每个 chunk 的结构如下：

```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion.chunk",
  "created": 1720000000,
  "model": "hy3",
  "choices": [
    {
      "index": 0,
      "delta": {
        "role": "assistant",
        "content": "人工智能"
      },
      "finish_reason": null
    }
  ]
}
```

### 各阶段 chunk 特征

| 阶段 | delta.role | delta.content | finish_reason |
|------|-----------|--------------|---------------|
| 首个 chunk | `"assistant"` | `""` 或空 | `null` |
| 中间 chunk | `null` | 文本片段 | `null` |
| 最后一个 chunk | `null` | `""` 或空 | `"stop"` |
| 结束标记 | — | — | `[DONE]` |

---

## 运行结果示例

```text
User: 请写一段关于人工智能未来发展的短文，大约200字左右。

Assistant:
--- 首 token 耗时: 1.23s ---

人工智能正在以前所未有的速度改变着我们的世界。未来，AI
将更加深入地融入日常生活，从智能家居到自动驾驶，从医疗
诊断到教育个性化，AI 的身影无处不在。大语言模型如 Hy3
将不断提升推理能力和知识广度，成为人类的高效协作伙伴。
同时，AI 的安全性和伦理问题也日益受到关注，确保技术发展
惠及全人类将是未来的重要课题。

--- 流式请求统计 ---
首 token 耗时:   1.23s
总耗时:          8.45s
生成 token 数:   ~187 字符
结束原因:        stop
```

---

## 流式处理的核心逻辑

```python
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": prompt}],
    stream=True,  # <-- 关键：开启流式
)

full_content = ""
for chunk in response:
    delta = chunk.choices[0].delta
    if delta.content:
        full_content += delta.content
        print(delta.content, end="", flush=True)  # 逐字输出

    if chunk.choices[0].finish_reason:
        print(f"\n结束原因: {chunk.choices[0].finish_reason}")
```

---

## 关键要点

1. **stream=True 是唯一变化**：其余参数（messages、temperature 等）完全一致
2. **逐个 chunk 处理**：每个 chunk 包含一个 `delta`（增量内容）而非完整消息
3. **需自行拼接**：流式模式下通常不返回 `usage`，需自行计数
4. **首 token 时延**：流式模式的首 token 到达时间通常远快于非流式的总响应时间
5. **`[DONE]` 标记**：流结束时收到 `data: [DONE]` 事件

---

## 参考

- [流式 vs 非流式对比](../03_streaming_comparison/streaming_comparison.md)
- [Quickstart - 参数说明](../Quickstart.md#核心参数说明)
- [TokenHub 控制台](https://console.cloud.tencent.com/tokenhub/apikey)
