# 01_basic_chat — 单轮 / 多轮对话

本示例演示如何通过 OpenAI 兼容 API 调用本地部署的腾讯混元 Hy3 模型，完成单轮与多轮对话。重点展示：

- 通过环境变量初始化客户端；
- 单轮对话：发送一条 `user` 消息并打印回复；
- 多轮对话：在 `messages` 中携带 `system` / `user` / `assistant` / `user` 历史记录再次调用，体现上下文延续。

## 简介

Hy3 提供 OpenAI 兼容的 `/v1/chat/completions` 接口，可直接使用 `openai` SDK 调用。本示例固定使用推荐参数 `temperature=0.9`、`top_p=1.0`，并通过 `extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}}` 关闭思考过程，得到直接回答。

## 完整请求代码

以下代码与 `../en/01_basic_chat.py` 完全一致：

```python
"""Hy3 示例 01：单轮 / 多轮对话。

通过 OpenAI 兼容 API 调用本地部署的 Hy3 模型，演示：
1. 单轮对话：发送一条用户消息并打印回复。
2. 多轮对话：携带 system / user / assistant / user 历史记录再次调用，
   展示上下文如何被带入下一轮。

连接信息通过环境变量读取，未设置时使用默认本地服务地址。
"""

import os

from openai import OpenAI

client = OpenAI(
    base_url=os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
    api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
)

MODEL = "hy3"


def chat(messages):
    """统一封装一次对话请求，固定使用推荐参数并关闭思考。"""
    return client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.9,
        top_p=1.0,
        extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
    )


def single_turn():
    """单轮对话：仅包含一条用户消息。"""
    print("=" * 60)
    print("【单轮对话】")
    print("=" * 60)

    messages = [
        {"role": "user", "content": "用一句话介绍腾讯混元 Hy3 模型。"},
    ]
    response = chat(messages)

    print(f"用户: {messages[0]['content']}")
    print(f"助手: {response.choices[0].message.content}")
    print()


def multi_turn():
    """多轮对话：把上一轮的 assistant 回复追加进 messages，再次调用。"""
    print("=" * 60)
    print("【多轮对话】")
    print("=" * 60)

    messages = [
        {"role": "system", "content": "你是一个简洁友好的中文助手。"},
        {"role": "user", "content": "Hy3 的上下文长度是多少？"},
        {"role": "assistant", "content": "Hy3 的上下文长度为 256K tokens。"},
        {"role": "user", "content": "那它的激活参数量是多少？"},
    ]
    response = chat(messages)

    for msg in messages:
        print(f"{msg['role']}: {msg['content']}")
    print(f"assistant: {response.choices[0].message.content}")
    print()


if __name__ == "__main__":
    single_turn()
    multi_turn()
```

## 完整 response 解析

`client.chat.completions.create(...)` 返回一个 `ChatCompletion` 对象，主要字段如下：

### 1. `response.id`

本次补全请求的唯一标识（字符串），例如 `chatcmpl-xxxx`。可用于日志追踪或问题排查。

```python
print(response.id)
# 示例: chatcmpl-9f2c1a8b7e6d4...
```

### 2. `response.choices[0].message.role`

模型本轮回复的角色，固定为 `"assistant"`。

```python
print(response.choices[0].message.role)
# assistant
```

### 3. `response.choices[0].message.content`

模型生成的文本内容，是日常使用中最常访问的字段。

```python
print(response.choices[0].message.content)
# 例如: Hy3 是腾讯混元团队推出的 295B 参数 MoE 大模型，激活参数约 21B。
```

> `choices` 是一个列表（通常长度为 1，对应 `n=1`），通过 `response.choices[0]` 取第一个候选结果，再取其 `.message`。

### 4. `response.usage`

本次调用的 token 用量统计，包含三个整数字段：

| 字段 | 含义 |
| --- | --- |
| `prompt_tokens` | 输入（含 system + 历史 + 本轮 user）的 token 数 |
| `completion_tokens` | 模型生成的 token 数 |
| `total_tokens` | 上述两者之和 |

```python
usage = response.usage
print(usage.prompt_tokens)      # 输入 token 数
print(usage.completion_tokens)  # 输出 token 数
print(usage.total_tokens)       # 总 token 数
```

### 访问路径速查

```
response
├── id                                # 请求 ID
├── choices[0]
│   ├── message
│   │   ├── role                      # "assistant"
│   │   └── content                   # 模型回复文本
│   └── finish_reason                 # 结束原因，如 "stop"
└── usage
    ├── prompt_tokens                 # 输入 token 数
    ├── completion_tokens             # 输出 token 数
    └── total_tokens                  # 总 token 数
```

## 示例输出

> 以下为代表性示例输出，并非真实运行结果，实际内容以模型返回为准。

```text
============================================================
【单轮对话】
============================================================
用户: 用一句话介绍腾讯混元 Hy3 模型。
助手: Hy3 是腾讯混元团队推出的 295B 参数 MoE 大模型，激活参数约 21B，支持 256K 上下文。

============================================================
【多轮对话】
============================================================
system: 你是一个简洁友好的中文助手。
user: Hy3 的上下文长度是多少？
assistant: Hy3 的上下文长度为 256K tokens。
user: 那它的激活参数量是多少？
assistant: Hy3 的激活参数量约为 21B。
```
