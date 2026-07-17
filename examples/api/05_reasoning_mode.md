# 05 Reasoning Mode：思考模式开关

源码：[`05_reasoning_mode.py`](05_reasoning_mode.py)

本示例针对 TokenHub 托管 API。项目 README 中的自托管 `chat_template_kwargs` 是另一套配置，不应与这里的参数同时发送。

## 运行

```bash
python 05_reasoning_mode.py
```

脚本会对同一问题分别请求一次关闭思考和一次高强度思考。

## 完整请求

关闭思考：

```python
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.2,
    top_p=1.0,
    max_tokens=2048,
    extra_body={"thinking": {"type": "disabled"}},
)
```

开启高强度思考：

```python
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.2,
    top_p=1.0,
    max_tokens=2048,
    extra_body={
        "thinking": {"type": "enabled"},
        "reasoning_effort": "high",
    },
)
```

## 完整响应解析

脚本分别解析：

- 扩展字段 `message.reasoning_content`；
- 最终答案 `message.content`；
- `finish_reason`；
- `usage`；
- 客户端总耗时。

某些 SDK 版本会把扩展字段放在 `model_extra`，示例的 `get_extra_field` 同时兼容属性和 `model_extra`。

## 示例输出

下面只展示输出形态；实际推理内容、Token 和耗时会变化：

```text
=== Thinking disabled ===
thinking=disabled, reasoning_effort=None
reasoning_content: <not returned>
answer: 需要 7.5 小时。
usage: {...}

=== Thinking enabled, effort=high ===
thinking=enabled, reasoning_effort=high
reasoning_content: 进水速率为 1/3，出水速率为 1/5……
answer: 两个管同时打开需要 7.5 小时注满。
usage: {...}
```

复杂数学、代码修复和多步决策适合开启思考；普通问答关闭思考通常有更低延迟和成本。
