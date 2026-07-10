# 示例 1：基本聊天 —— 单轮对话与多轮对话

## 概述

演示 Hy3 API 最基本的两种对话模式：

- **单轮对话**：一次请求 + 一次回答
- **多轮对话**：维护 messages 列表，实现上下文延续

---

## 前置条件

1. 在 [TokenHub 控制台](https://console.cloud.tencent.com/tokenhub/apikey) 创建 API Key
2. 安装 OpenAI SDK: `pip install openai`

---

## 完整请求

### 单轮对话请求

```json
{
  "model": "hy3",
  "messages": [
    {"role": "user", "content": "请用一句话解释什么是大语言模型（LLM）。"}
  ],
  "temperature": 0.9,
  "top_p": 1.0,
  "reasoning_effort": "no_think"
}
```

### 多轮对话请求（第三轮时的 messages）

```json
{
  "model": "hy3",
  "messages": [
    {"role": "system", "content": "你是一个乐于助人的助手，回答简洁明了。"},
    {"role": "user", "content": "法国的首都是什么？"},
    {"role": "assistant", "content": "法国的首都是巴黎。"},
    {"role": "user", "content": "那里有什么著名的地标建筑？"},
    {"role": "assistant", "content": "埃菲尔铁塔、卢浮宫、凯旋门等。"},
    {"role": "user", "content": "你能用英文介绍一下那个地标吗？"}
  ],
  "temperature": 0.7,
  "top_p": 1.0
}
```

---

## 完整响应解析

### 单轮响应

```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1720000000,
  "model": "hy3",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "大语言模型（LLM）是一种基于深度学习的人工智能模型，通过海量文本数据训练，能够理解和生成自然语言，完成问答、翻译、写作等多种任务。"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 26,
    "completion_tokens": 48,
    "total_tokens": 74
  }
}
```

### 关键字段说明

| 字段                          | 说明                                                          |
| ----------------------------- | ------------------------------------------------------------- |
| `id`                        | 唯一请求标识，可用于日志追踪                                  |
| `choices[].message.content` | 模型生成的回答内容                                            |
| `choices[].finish_reason`   | 结束原因：`stop`（正常结束）、`length`（达到 token 上限） |
| `usage.prompt_tokens`       | 输入消息的 token 数                                           |
| `usage.completion_tokens`   | 模型生成内容的 token 数                                       |
| `usage.total_tokens`        | 总 token 数                                                   |

---

## 运行结果示例

```text
============================================================
【单轮对话】
============================================================
模型回答: 大语言模型（LLM）是一种基于深度学习的人工智能模型，
通过海量文本数据训练，能够理解和生成自然语言，完成问答、
翻译、写作等多种任务。

--- 完整响应字段 ---
响应 ID:      chatcmpl-xxx
模型:         hy3
创建时间戳:   1720000000
结束原因:     stop
提示 token:   26
生成 token:   48
总 token:     74

============================================================
【多轮对话】
============================================================
User: 法国的首都是什么？
Assistant: 法国的首都是巴黎。

User: 那里有什么著名的地标建筑？
Assistant: 巴黎有许多著名地标，包括埃菲尔铁塔、卢浮宫、
凯旋门、巴黎圣母院和塞纳河畔的奥赛博物馆等。

User: 你能用英文介绍一下那个地标吗？
Assistant: Of course! The Eiffel Tower (La Tour Eiffel) is
an iconic wrought-iron lattice tower located on the Champ
de Mars in Paris. Built in 1889, it stands 330 meters tall
and is one of the most recognizable structures in the world.

--- 多轮对话统计 ---
总消息数: 7
总 token 数: 156
```

---

## 关键要点

1. **messages 是有序列表**：每次对话将 user 和 assistant 消息按顺序追加，模型会看到完整上下文
2. **system prompt**：可选，用于设定助手的行为风格
3. **单轮 vs 多轮**：技术层面没有区别，多轮只是累积更多的 messages
4. **token 统计**：`usage` 字段可以帮助你估算成本和上下文长度

---

## 参考

- [Quickstart](../Quickstart.md) — 基本参数说明
- [TokenHub 控制台](https://console.cloud.tencent.com/tokenhub/apikey) — 获取 API Key
- [错误处理示例](../06_error_handling/error_handling.md) — 处理 API 异常
