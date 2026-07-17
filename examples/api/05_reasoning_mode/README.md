# 05 Reasoning Mode — 思考过程开 / 关对比

对比托管 API 上关闭 / 开启深度思考时，响应字段与 token 用量的差异。

## 运行

```bash
cd examples/api
python 05_reasoning_mode/main.py
```

## 完整请求

### 关闭思考

```json
{
  "model": "hy3",
  "messages": [
    {
      "role": "user",
      "content": "小明有 5 个苹果，给了小红 2 个，又买了 3 个，最后还剩几个？只给最终数字和一句理由。"
    }
  ],
  "temperature": 0.9,
  "max_tokens": 512,
  "thinking": {"type": "disabled"}
}
```

### 开启思考

```json
{
  "model": "hy3",
  "messages": [
    {
      "role": "user",
      "content": "小明有 5 个苹果，给了小红 2 个，又买了 3 个，最后还剩几个？只给最终数字和一句理由。"
    }
  ],
  "temperature": 0.9,
  "max_tokens": 8192,
  "thinking": {"type": "enabled"},
  "reasoning_effort": "high"
}
```

Python SDK（非标字段走 `extra_body`）：

```python
resp = client.chat.completions.create(
    model="hy3",
    messages=[...],
    max_tokens=8192,
    extra_body={
        "thinking": {"type": "enabled"},
        "reasoning_effort": "high",
    },
)
msg = resp.choices[0].message
print(getattr(msg, "reasoning_content", None))
print(msg.content)
```

## 响应解析

| 模式 | `content` | `reasoning_content` | 建议 `max_tokens` |
|---|---|---|---|
| `thinking.type=disabled` | 最终答案 | 通常无 | 较小即可 |
| `thinking.type=enabled` | 最终答案 | 思考过程文本 | 明显加大（思考与答案共享额度） |

也可用单独的 `reasoning_effort`（`low` / `medium` / `high`）控制强度。官方文档默认约为 `low`。

## 示例输出（脱敏）

```text
=== Response parse (thinking-off) ===
{
  "role": "assistant",
  "content": "6。因为先减 2 再加 3。"
}
usage: prompt=42 completion=18 total=60

=== Response parse (thinking-on) ===
{
  "role": "assistant",
  "content": "最终还剩 6 个苹果。",
  "reasoning_content": "5-2=3，再 +3 → 6。…"
}
usage: prompt=42 completion=126 total=168

=== Diff summary ===
thinking-off has reasoning_content: False
thinking-on  has reasoning_content: True
```

## 与本地部署的差异

| 场景 | 参数 |
|---|---|
| TokenHub 托管（本示例） | 顶层 `thinking` / `reasoning_effort` |
| vLLM / SGLang 本地 | `extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think\|low\|high"}}` |

不要把本地参数原样拷到托管 API。
