# 03 Non-streaming vs Streaming：时延对比

源码：[`03_latency_comparison.py`](03_latency_comparison.py)

## 运行

```bash
python 03_latency_comparison.py
```

此示例会产生两次独立请求。

## 完整请求

两次请求使用相同的 `model`、`messages`、采样参数和输出上限。非流式调用：

```python
start = time.perf_counter()
response = client.chat.completions.create(**request)
total = time.perf_counter() - start
```

流式调用：

```python
start = time.perf_counter()
stream = client.chat.completions.create(
    **request,
    stream=True,
    stream_options={"include_usage": True},
)
for chunk in stream:
    if first_visible is None and chunk.choices and (
        chunk.choices[0].delta.content or reasoning_content
    ):
        first_visible = time.perf_counter() - start
total = time.perf_counter() - start
```

## 响应和计时解析

- 非流式只能在完整响应返回后显示内容，客户端无法从该响应单独测量服务端 TTFT，因此“首次可见时间”等于总耗时。
- 流式首个可见 chunk 时间从发送请求计到收到第一个非空 `content` 或 `reasoning_content`。
- 流式总耗时计到迭代器结束。
- 两种模式分别解析正文、`finish_reason` 和 `usage`。

这不是严格性能基准。网络、队列、缓存、生成长度和两次采样结果都会影响数据；脚本不会错误地断言两次输出完全一致。

## 示例输出

以下数字仅为格式示意，不代表 Hy3 的固定性能：

```text
=== Timing comparison ===
non-streaming first visible / total: 4.812s
streaming first visible chunk: 0.963s
streaming total: 4.991s
non-streaming chars: 276
streaming chars: 284
non-streaming usage: {'prompt_tokens': 31, 'completion_tokens': 184, ...}
streaming usage: {'prompt_tokens': 31, 'completion_tokens': 191, ...}
```
