# 示例 01：基础对话（单轮 & 多轮）

> 对应脚本：[`01_basic_chat.py`](01_basic_chat.py)

本地部署（vLLM / SGLang）后，用 OpenAI 兼容 SDK 完成第一次对话。本示例演示单轮和带历史的多轮两种用法。

## 前置条件

- 已本地启动 Hy3 服务，`base_url` 默认为 `http://127.0.0.1:8000/v1`
- `HY3_API_KEY` 可用占位符 `EMPTY`
- 模型名默认 `hy3`

```bash
export HY3_BASE_URL='http://127.0.0.1:8000/v1'
export HY3_API_KEY='EMPTY'
export HY3_MODEL='hy3'
```

## 完整请求

**curl（单轮）：**

```bash
curl "$HY3_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $HY3_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "hy3",
    "messages": [{"role": "user", "content": "用一句话解释什么是 API。"}],
    "max_tokens": 256,
    "chat_template_kwargs": {"reasoning_effort": "no_think"}
  }'
```

**Python（与脚本一致）：**

```python
response = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": "用一句话解释什么是 API。"}],
    temperature=0.9,
    top_p=1.0,
    max_tokens=256,
    extra_body=REASONING,   # {"chat_template_kwargs": {"reasoning_effort": "no_think"}}
)
```

## 完整响应解析

返回对象（SDK 类型 `ChatCompletion`）结构如下：

```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "model": "hy3",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "API（应用程序编程接口）是不同软件之间相互调用的约定与工具。"
    },
    "finish_reason": "stop"
  }],
  "usage": {"prompt_tokens": 16, "completion_tokens": 42, "total_tokens": 58}
}
```

| 路径 | 含义 |
|---|---|
| `choices[0].message.content` | 模型回答文字（单轮取第一个候选） |
| `choices[0].finish_reason` | 结束原因：`stop`=正常说完，`length`=被 `max_tokens` 截断 |
| `usage.prompt_tokens` | 输入消耗的 token |
| `usage.completion_tokens` | 输出消耗的 token |
| `usage.total_tokens` | 两者之和，即本次调用总账 |

> 为什么是 `choices[0]`？接口支持一次返回多个候选（OpenAI 兼容设计），默认只给 1 个，所以永远取第一个。

## 多轮对话

模型本身不具有记忆。多轮对话中每轮将**完整的 messages 历史**重新发给服务器：

```python
messages = [
    {"role": "system", "content": "你是一个简洁、准确的编程助手。"},
    {"role": "user", "content": "Python 列表推导式是什么？"},
]
r1 = client.chat.completions.create(model=MODEL, messages=messages, ...)
# 把 assistant 回复追加进历史，再追加下一个 user 问题
messages.append({"role": "assistant", "content": r1.choices[0].message.content})
messages.append({"role": "user", "content": "给一个只保留偶数的例子。"})
r2 = client.chat.completions.create(model=MODEL, messages=messages, ...)
```

`role` 取值：`system`（人设）、`user`（你）、`assistant`（模型）、`tool`（工具结果，见示例 04）。

## 示例输出

~~~
=== 单轮对话 ===
回答：API（应用程序编程接口）是一套预先定义的规则和协议，让不同的软件系统能够相互通信、交换数据或调用功能。
结束原因: stop
Token 用量：CompletionUsage(completion_tokens=28, prompt_tokens=21, total_tokens=49, completion_tokens_details=CompletionTokensDetails(accepted_prediction_tokens=None, audio_tokens=None, reasoning_tokens=0, rejected_prediction_tokens=None), prompt_tokens_details=PromptTokensDetails(audio_tokens=None, cached_tokens=0))

=== 多轮对话 ===
助手：Python 列表推导式（List Comprehension）是一种**用简洁语法基于可迭代对象快速生成列表**的方式。

基本语法：
```python
[表达式 for 变量 in 可迭代对象 if 条件]
```

示例：
```python
# 生成 0~4 的平方
squares = [x**2 for x in range(5)]
# 结果：[0, 1, 4, 9, 16]

# 带条件：只取偶数平方
even_squares = [x**2 for x in range(10) if x % 2 == 0]
# 结果：[0, 4, 16, 36, 64]
```

优点：
- 代码更短、可读性高
- 通常比等价 for 循环更快

等价普通写法：
```python
squares = []
for x in range(5):
    squares.append(x**2)
```

也可支持多层循环：
```python
pairs = [(x, y) for x in range(3) for y in range(2)]
```

助手： ```python
evens = [x for x in range(10) if x % 2 == 0]
# 结果：[0, 2, 4, 6, 8]
```

解释：遍历 0~9，只保留能被 2 整除（即偶数）的元素。
~~~
