# 05 思考模式（Reasoning modes）

这个示例用同一道题比较 Hy3 的 `off`、`low`、`medium`、`high` 四档，并分别读取
思考内容、最终答案、结束原因、token 用量和耗时。完整代码见
[05_reasoning_mode.py](05_reasoning_mode.py)。

## 请求

关闭思考：

```python
extra_body={"thinking": {"type": "disabled"}}
```

开启并选择深度：

```python
extra_body={
    "thinking": {"type": "enabled"},
    "reasoning_effort": "low",  # 或 medium/high
}
```

脚本对每个模式发送相同请求：

```python
response = create_chat_completion(
    client,
    model=config.model,
    messages=[{"role": "user", "content": "有三个盒子标签都贴错了，怎样只取一次球确定每个盒子的内容？"}],
    temperature=0,
    max_tokens=max_tokens,
    extra_body=body,
)
```

运行全部文档模式，或只选部分模式：

```powershell
python examples/api/05_reasoning_mode.py
python examples/api/05_reasoning_mode.py --modes off low high
```

简单演示默认 `max_tokens=4096`；可用 `HY3_REASONING_MAX_TOKENS` 调整。复杂推理中
推理 token 与答案共享额度，官方建议显著提高预算并对长输出使用 streaming。

## 运行结果

以下数据采集于 2026-07-17，使用 TokenHub 广州入口、`model=hy3`、
`temperature=0` 和 `max_tokens=4096`。`reasoning_chars` 是完整
`reasoning_content` 的字符数；文档只列统计，脚本会打印完整字段。

| mode | 耗时（秒） | finish | reasoning_chars | prompt tokens | completion tokens | total tokens |
|---|---:|---|---:|---:|---:|---:|
| off | 6.849 | stop | 0 | 33 | 336 | 369 |
| low | 20.375 | stop | 1189 | 30 | 1243 | 1273 |
| medium | 22.399 | stop | 1328 | 30 | 1395 | 1425 |
| high | 28.904 | stop | 1620 | 30 | 1530 | 1560 |

四档最终答案都正确选择从贴“红白”标签的盒子取一次球。`off` 档实际答案的结论为：

```text
只从贴“红白”标签的盒子里取一个球，看颜色，就能确定三个盒子的真实内容。
```

这些都是单次样本，只说明字段形态和本次成本/时延，不能据此断言档位间的稳定质量
排名。尤其不能把本轮 token 数当成未来请求的固定值。

## 容易踩坑

- Hosted API 不使用本地部署参数 `chat_template_kwargs.reasoning_effort=no_think`。
- 关闭 thinking 时不要继续发送 effort。
- 只打印最终答案会漏掉 reasoning，也看不到 `finish_reason=length` 截断。
