# 03 Latency Compare — 非流式 vs 流式时延

对比同 prompt 下非流式与流式的 **首 token 时延（TTFT）** 与 **总耗时**。

## 运行

```bash
cd examples/api
python 03_latency_compare/main.py
```

## 指标定义

| 指标 | 非流式 | 流式 |
|---|---|---|
| TTFT | 收到完整响应体的时间（首包即全文） | 收到第一个非空 `delta.content` 的时间 |
| Total | 请求开始 → 响应结束 | 请求开始 → 流结束 |

## 完整请求

非流式：

```json
{
  "model": "hy3",
  "messages": [{"role": "user", "content": "用不超过 80 字说明什么是首 token 时延（TTFT）。"}],
  "temperature": 0.9,
  "max_tokens": 256,
  "stream": false
}
```

流式：同上，但 `"stream": true`。

## 响应解析 / 计时伪代码

```python
# non-stream
t0 = time.perf_counter()
resp = client.chat.completions.create(..., stream=False)
total = time.perf_counter() - t0
ttft = total  # 全文一次性返回

# stream
t0 = time.perf_counter()
ttft = None
for chunk in client.chat.completions.create(..., stream=True):
    piece = chunk.choices[0].delta.content if chunk.choices else None
    if piece and ttft is None:
        ttft = time.perf_counter() - t0
total = time.perf_counter() - t0
```

## 示例输出（脱敏样例）

```text
=== Latency compare ===
[non-stream] ttft_ms=1842.3  total_ms=1842.3  chars=42  preview='TTFT 是从发出请求到收到第一个输出 token 的时间。'
[stream]     ttft_ms=312.7   total_ms=1905.1  chars=45  preview='TTFT 是从发出请求到收到第一个输出 token 的时间。'

=== How to read ===
- Non-stream: client waits for full JSON; TTFT ≈ total.
- Stream: TTFT is usually much smaller; total may be similar or slightly higher.
```

> 数值受网络、地域入口、负载与输出长度影响，请以本机实测为准。交互场景优先流式以降低体感等待。
