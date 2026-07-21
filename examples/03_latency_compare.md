# 示例 03：时延对比（非流式 vs 流式）

> 对应脚本：[`03_latency_compare.py`](03_latency_compare.py)

对比两种模式下的“首 token 时延（TTFT）”和“总耗时”，帮助判断是否采用流式。

## 测量原理

- **非流式总耗时**：从发请求到拿到完整响应之间的墙钟时间。
- **流式 TTFT（Time To First Token）**：从发请求到收到第一个 `delta.content` 的时间——用户“感觉到的响应速度”。
- **流式总耗时**：从发请求到 `finish_reason` 出现的时间。

用 `time.perf_counter()` 计时 ，先做 warm-up 消除冷启动，再多次测量取 P50 / P95。

## 完整请求

本示例内部调用 `measure_non_stream` 与 `measure_stream` 两个函数，请求参数与普通对话一致：

```python
# 非流式
client.chat.completions.create(model=MODEL, messages=[...], max_tokens=512, extra_body=REASONING)
# 流式
client.chat.completions.create(model=MODEL, messages=[...], max_tokens=512,
                               stream=True, stream_options={"include_usage": True}, extra_body=REASONING)
```

命令行参数：

```bash
python 03_latency_compare.py              # 默认 3 次正式 + 1 次热身
python 03_latency_compare.py --runs 5 --warmup 2
```

## 完整响应解析

本示例**不解析回答内容**，只计时并统计；需要解析内容 / usage 时，写法同示例 01 / 02。

流式循环中，第一个内容 chunk 到来即记录 TTFT，遇到 `finish_reason` 即结束计时：

```python
for chunk in stream:
    if not chunk.choices:           # usage 尾块：空 choices，仅带 usage，可忽略
        continue
    if ttft is None and chunk.choices[0].delta.content:
        ttft = time.perf_counter() - start
    if chunk.choices[0].finish_reason:
        break
```

## 示例输出

```
热身 1 次...
正式测量 3 次...

  Run 1/3: 非流式=9.84s  流式TTFT=8.52s  流式总计=9.23s
  Run 2/3: 非流式=8.74s  流式TTFT=7.36s  流式总计=8.70s
  Run 3/3: 非流式=9.40s  流式TTFT=8.34s  流式总计=8.34s

========================================
        非流式总耗时: 平均=9.33s  P50=9.40s  P95=9.84s
          流式TTFT: 平均=8.07s  P50=8.34s  P95=8.52s
        流式总耗时: 平均=8.76s  P50=8.70s  P95=9.23s

  流式感知加速比(以首字计): ~1.2x
```

结论：本机测试流式感知加速比约 **1.2x**，增益取决于服务负载与输出长度。在负载较低或输出较长时，TTFT 优势会更明显。
