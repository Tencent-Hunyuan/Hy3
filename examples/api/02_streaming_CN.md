# 02 流式输出

[English](02_streaming.md) · [索引](README_CN.md) · [脚本](02_streaming.py)

## 用途

在不假设每个 chunk 都含文本的前提下消费流式 completion。[`02_streaming.py`](02_streaming.py) 会实时打印 content，同时在最终快照中保留 reasoning、usage、finish reason 和工具调用分片。

## 配置

通过 `examples/api/.env` 配置后端。请求使用当前后端的 `no_think` 映射，并要求后端在流中包含 usage。兼容服务不一定提供所有可选字段。

## 完整请求

`build_request` 返回的完整 SDK 参数为：

```python
{
    "model": config.model,
    "messages": [
        {
            "role": "user",
            "content": "Explain what an API is in two sentences.",
        }
    ],
    "temperature": 0.9,
    "top_p": 1.0,
    "max_tokens": 512,
    "stream": True,
    "stream_options": {"include_usage": True},
    "extra_body": reasoning_extra_body(config, "no_think"),
}
```

## 响应解析

对每个 chunk，`StreamAccumulator.add_chunk` 按以下顺序处理：

1. 在检查 choices 前规范化并保存在布尔判断中为真的非空 `usage`，因此能处理结尾的 usage-only chunk。
2. `choices=[]` 时返回空 update；空 choices chunk 是合法的。
3. 只读取第一个 choice，保存非空 finish reason，并分别提取 content 与 reasoning。
4. 追加非空 content/reasoning 分片，并扩展结构化 reasoning details。
5. 按整数 `index` 重组工具调用的 `id`、`function.name` 和 `function.arguments`。分片可以交错到达，最终结果按 index 排序。

`consume_stream` 只打印 `update.content`，reasoning 不会出现在实时 `Content:` 行中。`result()` 会对嵌套 usage、reasoning details 和 tool calls 生成独立副本。

## 运行

从仓库根目录运行：

```bash
python examples/api/02_streaming.py
```

命令使用已配置 API。第一个区块记录一次实时运行；第二个区块仍是用于说明流式分片行为的离线 accumulator fixture。

## 示例输出

**已验证在线证据摘要（已脱敏，并非逐字标准输出）**

脚本实际 CLI 会使用代码中固定的英文标签，流式打印 `Content:`，随后打印 JSON 摘要。下列列表是经过审查的摘要，并非运行记录转录：

- 后端：OpenRouter
- 请求模型：`tencent/hy3:free`
- 响应模型：该脚本保留的结果中不可用
- 观测日期：2026-07-11
- Content：用两句话解释 API
- Reasoning：空
- Finish reason：`stop`
- `usage.total_tokens`：77
- Tool calls：空列表

**确定性离线示例**

```text
content: Hello world
reasoning: plan carefully
finish_reason: tool_calls
usage.total_tokens: 12
tool_calls[0]: call_weather / get_weather / {"city":"Shenzhen"}
tool_calls[1]: call_time / get_time / {"timezone":"Asia/Hong_Kong"}
```

该 fixture 会先发送空 chunk，在后续 chunk 中让 index 1 的调用先于 index 0 到达，并以 usage-only chunk 结束。

## 限制与注意事项

- 实时 content 描述是摘要，不是精确输出断言；确定性区块是合成测试数据。
- `stream_options.include_usage` 只能请求 usage，无法强制不支持的后端返回。
- accumulator 只读取第一个 choice。
- 脚本实时打印 content，但 reasoning、usage 和重组后的工具调用要等流结束后才输出。
- 如果网络在结尾 chunk 前中断，finish reason 或 usage 可能不可用。
