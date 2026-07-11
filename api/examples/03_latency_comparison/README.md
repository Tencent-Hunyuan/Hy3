# Non-streaming vs streaming：时延对比

运行：

```bash
python api/examples/03_latency_comparison/latency_comparison.py
```

完整请求和解析见 [`latency_comparison.py`](latency_comparison.py)。脚本对同一请求分别调用非流式与流式接口；使用单调高精度计时器 `time.perf_counter()`，从发起请求计到第一个非空 content token 得到首 token 时延（TTFT），迭代结束得到总耗时。

```python
request = {
    "model": model,
    "messages": [{"role": "user", "content": "解释什么是二分查找。"}],
    "max_tokens": 512,
    "extra_body": {"chat_template_kwargs": {"reasoning_effort": "no_think"}},
}
response = client.chat.completions.create(**request)
stream = client.chat.completions.create(**request, stream=True)
```

两次调用的采样输出可能不同，因此这里比较的是用户可感知时延，不是严格的服务端基准。正式压测应预热模型、固定采样参数并重复多次统计分位数。

```text
=== Non-streaming ===
id: chatcmpl-c21
model: hy3
content: 二分查找是在有序序列中反复折半搜索范围的算法。
finish_reason: stop
usage: prompt=14, completion=26, total=40
total latency: 1.842s

=== Streaming ===
content: 二分查找通过比较中间元素，不断将有序搜索区间缩小一半。
first token latency: 0.214s
total latency: 1.906s
finish_reason: stop
usage: prompt=14, completion=31, total=45
```
