# 03 非流式与流式时延对比

这个示例用相同 prompt 和参数重复测量两种请求：非流式记录总耗时，流式记录首个
可见正文的时间（TTFT）和总耗时。完整代码见
[03_latency_compare.py](03_latency_compare.py)。

## 请求和测量方式

基础请求固定为：

```python
request = {
    "model": config.model,
    "messages": [{"role": "user", "content": "用三句话解释二分查找。"}],
    "temperature": 0,
    "max_tokens": 512,
    "extra_body": {"thinking": {"type": "disabled"}},
}
```

非流式从调用前计时到完整响应返回；流式从调用前计时到第一个非空 content delta
得到 TTFT，迭代到 finish/usage 尾块得到总耗时。计时包含公共有限重试产生的等待，
每个样本同时记录 `transient_retries`。默认先预热 1 对，再测量 5 对，输出每次原始值
和线性插值 P50/P95：

```powershell
python examples/api/03_latency_compare.py --warmup 1 --runs 5
```

## 运行结果

这些值是客户端观测结果，包含网络、网关、排队和模型生成时间。服务端 SLA 需使用
官方监控口径。对比时应固定地区、网络、prompt、model 和参数，回答质量需单独评估。

2026-07-17 在 TokenHub 广州入口以 `model=hy3`、预热 1 对、测量 5 对实测如下
（秒，按实际运行顺序；本轮所有样本 `transient_retries=0`）：

| 模式 | 原始样本 | P50 | P95 |
|---|---|---:|---:|
| non-streaming 总耗时 | 2.106, 1.981, 2.074, 2.291, 1.957 | 2.074 | 2.254 |
| streaming TTFT | 0.652, 0.666, 0.692, 0.660, 0.752 | 0.666 | 0.740 |
| streaming 总耗时 | 1.645, 1.766, 1.844, 1.693, 1.726 | 1.726 | 1.828 |

10 个测量请求均为 `finish_reason=stop`；5 个流式结果均 `complete=true`。这份客户端
快照只对应本次地域、时段、prompt 和输出长度。

## 容易踩坑

- TTFT 从请求开始计时，到第一个可见 content delta 到达为止。
- 计时使用单调时钟，例如 `time.perf_counter()`。
- 重复测量，并把 reasoning delta 排除在用户可见正文之外。
