# 03 流式与非流式对比

[English](03_streaming_vs_non_streaming.md) · [索引](README_CN.md) · [脚本](03_streaming_vs_non_streaming.py)

## 用途

展示两种 API 形式能够观察到哪些延迟。[`03_streaming_vs_non_streaming.py`](03_streaming_vs_non_streaming.py)测量非流式总耗时、流式首次输出、流式首次可见 content 和流式总耗时。

## 配置

通过 `examples/api/.env` 配置后端。需要在正式比较前发送一次不计时请求时使用 `--warmup`。两种测量使用相同问题、model、temperature、top-p、token 上限和推理映射。

## 完整请求

共享的基础请求为：

```python
request = {
    "model": config.model,
    "messages": [
        {
            "role": "user",
            "content": "Explain idempotency in APIs in three sentences.",
        }
    ],
    "temperature": 0.9,
    "top_p": 1.0,
    "max_tokens": 256,
    "extra_body": reasoning_extra_body(config, "no_think"),
}
```

非流式调用原样发送该 dict。流式调用创建一个新 dict，只增加两个字段：

```python
stream_request = {
    **request,
    "stream": True,
    "stream_options": {"include_usage": True},
}
```

启用 warmup 时，会在两次测量前额外发送一次未修改的基础请求。

## 响应解析

- `measure_non_streaming` 在 SDK 调用前后记录一个时间区间。
- `measure_streaming` 记录 `started`，再用 `StreamAccumulator` 逐个消费 chunk。
- **首次输出**是第一个非空 reasoning 或 content update。
- **首次可见 content**是第一个非空 content update；reasoning 可能更早到达，但不会作为用户可见内容打印。
- **总耗时**在整个 stream 迭代结束后记录。

函数只返回 timing dataclass，不保留或比较回答文本。因此该示例展示计时机制，而不是响应质量。

## 运行

从仓库根目录运行：

```bash
python examples/api/03_streaming_vs_non_streaming.py
python examples/api/03_streaming_vs_non_streaming.py --warmup
```

这些命令使用已配置 API 和实时 clock。第一个区块是未启用 warmup 的一次实时观测；第二个区块使用注入的测试 clock。

## 示例输出

**已验证在线证据摘要（已脱敏，并非逐字标准输出）**

脚本实际 CLI 会使用代码中固定的英文计时标签。下列列表是经过审查的单次观测摘要，并非运行记录转录或 benchmark：

- 后端：OpenRouter
- 请求模型：`tencent/hy3:free`
- 响应模型：该脚本保留的结果中不可用
- 观测日期：2026-07-11
- 非流式总耗时：4.465s
- 流式首次输出：1.306s
- 流式首次可见 content：1.306s
- 流式总耗时：3.175s

这些数值只是一次瞬时观测，不是 benchmark，也不表示流式始终更快。

**确定性离线示例**

```text
Non-streaming total: 0.750s
Streaming first output: 0.100s
Streaming first content: 0.400s
Streaming total: 1.000s
```

非流式和流式数值来自确定性单元测试 clock。它们只是解析和格式化 fixture，不是实时 benchmark，也不能证明某一种模式更快。

## 限制与注意事项

- 不要把单次实时观测或 fixture 数值泛化为 benchmark。
- 公平的实时比较需要重复试验、受控负载、相同后端以及相同 prompt/采样设置。
- 没有 reasoning/content delta 时，`first_output_seconds` 或 `first_content_seconds` 为 `None`，CLI 会打印 `unavailable`。
- 示例不验证两次回答在语义上等价。
- warmup 会改变服务端/client 状态，发布测量结果时必须说明是否启用。
