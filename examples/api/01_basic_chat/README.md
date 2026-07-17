# 01 Basic Chat — 单轮 / 多轮对话

演示最基础的 Chat Completions 调用：单轮提问，以及带 `system` + 历史的多轮续写。

## 运行

```bash
cd examples/api
python 01_basic_chat/main.py
```

## 完整请求（单轮）

```json
{
  "model": "hy3",
  "messages": [
    {"role": "user", "content": "用一句话介绍你自己。"}
  ],
  "temperature": 0.9,
  "top_p": 1.0,
  "max_tokens": 256
}
```

等价 Python：

```python
resp = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "用一句话介绍你自己。"}],
    temperature=0.9,
    top_p=1.0,
    max_tokens=256,
)
print(resp.choices[0].message.content)
```

## 完整请求（多轮）

`messages` 顺序：`system`（可选）→ `user` → `assistant` → `user` → …，且必须以 `user` 结尾。

```json
{
  "model": "hy3",
  "messages": [
    {"role": "system", "content": "你是简洁的编程助手，回答控制在两句话内。"},
    {"role": "user", "content": "Python 怎么读取 JSON 文件？"},
    {"role": "assistant", "content": "用内置 json 模块：import json; data = json.load(open('a.json'))。"},
    {"role": "user", "content": "如果文件很大怎么办？"}
  ]
}
```

## 响应解析

| 字段 | 含义 |
|---|---|
| `choices[0].message.role` | 通常为 `assistant` |
| `choices[0].message.content` | 最终回答文本 |
| `choices[0].finish_reason` | `stop` 正常结束；`length` 触及 `max_tokens` |
| `usage.prompt_tokens` / `completion_tokens` / `total_tokens` | 用量统计 |

## 示例输出（脱敏）

```text
=== Single-turn ===
finish_reason: stop
content: 你好！我是混元 Hy3，由腾讯混元团队研发的大模型助手。
usage: prompt=18 completion=28 total=46

=== Multi-turn ===
{
  "role": "assistant",
  "content": "大文件可用流式解析（如 ijson），或按行读取 NDJSON，避免一次性载入内存。"
}
```

> 实际文案会因采样而变化；结构字段保持一致。
