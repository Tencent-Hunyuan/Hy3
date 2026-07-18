# 02 · Streaming

## 说明

使用 `stream=True` 接收增量 token，并拼接完整回复。

## 运行

```bash
python 02_streaming.py
```

## 请求

```python
stream = client.chat.completions.create(..., stream=True)
for chunk in stream:
    piece = chunk.choices[0].delta.content  # 可能为 None
```

## 响应

- 增量内容在 `delta.content`
- 客户端自行拼接完整文本

## 示例输出

```text
=== streaming ===
人工智能是模拟人类智能的计算机技术。它能学习、推理并自主完成任务。已广泛应用于医疗、交通等领域。
--- assembled ---
人工智能是模拟人类智能的计算机技术。它能学习、推理并自主完成任务。已广泛应用于医疗、交通等领域。
```
