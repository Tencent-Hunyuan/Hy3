# Example 2: Streaming — 流式请求 & 逐 chunk 解析

## 请求

```python
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "用 50 字以内介绍深度学习。"}],
    stream=True,
)

for chunk in response:
    delta = chunk.choices[0].delta
    if delta.content:
        print(delta.content, end="", flush=True)
```

## chunk 结构

| 阶段 | choices[0].delta | finish_reason |
|------|------------------|---------------|
| 1 | `{"role": "assistant"}` | null |
| 2~n-1 | `{"content": "xxx"}` | null |
| 最后一个 | `{}` | `"stop"` |

### 序列示例

```
chunk 1:  delta={"role":"assistant"}                    finish_reason=null
chunk 2:  delta={"content":"深度"}                       finish_reason=null
chunk 3:  delta={"content":"学习"}                       finish_reason=null
...
chunk N:  delta={}                                       finish_reason="stop"
```

## 示例输出

```
Streaming response (逐 token 打印):
----------------------------------------
深度学习是机器学习的一个分支，利用多层神经网络学习数据表示，在图像识别、自然语言处理等领域取得了突破性进展。

--- 最后一个 chunk ---
chunk.id: chatcmpl-xxx
finish_reason: stop
usage: CompletionUsage(prompt_tokens=14, completion_tokens=38, total_tokens=52)
```
