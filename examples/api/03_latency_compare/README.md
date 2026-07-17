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

## 示例输出（2026-07-18 TokenHub 实测）

```text
=== Latency compare ===
[non-stream] ttft_ms=1959.5  total_ms=1959.5  chars=81
  preview='首 token 时延（TTFT）指用户发起请求到大模型生成第一个输出 token 所耗时间…'
[stream]     ttft_ms=664.4   total_ms=1319.0  chars=77
  preview='首 token 时延（TTFT）指用户发起请求到模型生成第一个输出 token 的等待时间…'

=== How to read ===
- Non-stream: client waits for full JSON; TTFT ≈ total.
- Stream: TTFT is usually much smaller; total may be similar or slightly higher.
```

> 数值受网络、地域入口、负载与输出长度影响，请以本机实测为准。本次流式 TTFT（约 0.66s）明显低于非流式全文等待（约 1.96s）。
