# 05 推理模式

[English](05_reasoning_mode.md) · [索引](README_CN.md) · [脚本](05_reasoning_mode.py)

## 用途

在保持问题和标准请求字段不变时比较 `no_think` 与 `high`。[`05_reasoning_mode.py`](05_reasoning_mode.py)记录每种模式的规范化 reasoning、content、usage 和耗时。

## 配置

在 `examples/api/.env` 中配置任一后端。对比函数只接受 `no_think` 和 `high`；传入 `low` 会在读取 clock 或调用 SDK 前抛出 `ValueError`。

不同后端的映射如下：

| 对比模式 | 自部署 SDK `extra_body` | OpenRouter SDK `extra_body` |
|---|---|---|
| `no_think` | `{"chat_template_kwargs": {"reasoning_effort": "no_think"}}` | `{"reasoning": {"effort": "none"}}` |
| `high` | `{"chat_template_kwargs": {"reasoning_effort": "high"}}` | `{"reasoning": {"effort": "high"}}` |

## 完整请求

两次调用使用完全相同的问题和标准字段：

```python
QUESTION = "A train travels 120 km in 2 hours. What is its average speed?"

client.chat.completions.create(
    model=config.model,
    messages=[{"role": "user", "content": QUESTION}],
    temperature=0.9,
    top_p=1.0,
    max_tokens=512,
    extra_body=reasoning_extra_body(config, effort),
)
```

`main` 复用同一个 client，并按以下顺序调用 `run_mode`：

```python
for effort in ("no_think", "high"):
    result = run_mode(client, config, effort, QUESTION)
```

## 响应解析

`summarize_completion` 会规范化 content、reasoning 文本、结构化 reasoning details、finish reason 和 usage。`ModeResult` 保留：

- 请求的 effort；
- 规范化的 reasoning 和 details；
- content，缺失时转为空字符串；
- 注入或默认的 `clock` 时钟函数计算的 elapsed 秒数；
- 普通 dict 形式的 usage，或 `None`。

reasoning 缺失是合法状态。只有 reasoning 文本和 details 都为空时，`main` 才打印 unavailable 提示；响应仍可包含有效 assistant content。

## 运行

从仓库根目录运行：

```bash
python examples/api/05_reasoning_mode.py
```

该命令使用已配置后端。下方内容使用确定性 fake completion 和注入 clock。

## 示例输出

**确定性离线示例**

```text
no_think:
  content: 60 km/h
  reasoning: ""
  reasoning_details: []
  elapsed: 0.100s
  usage.total_tokens: 7

high:
  content: 60 km/h
  reasoning: distance divided by time
  reasoning_details: []
  elapsed: 0.300s
  usage.total_tokens: 7
```

以上时间来自注入的单元测试 clock，不是实时延迟测量。

## 限制与注意事项

- fixture 不能证明某种模式更快或更准确。
- reasoning 字段是可选且依赖后端的；缺失 reasoning 不是错误。
- 对比只覆盖 `no_think` 和 `high`，不覆盖 `low`。
- 展示模型 reasoning 前，请先审查提供方行为和产品策略。
- `frozen=True` 只能阻止替换 dataclass 字段，嵌套 list/dict 仍是普通 Python 容器。
