# Basic Chat — 单轮与多轮对话

演示 Hy3 API 的基础对话能力，包含单轮问答和多轮上下文对话。多轮对话通过将历史的 assistant 回复加入 `messages` 列表来实现上下文传递。

## 运行

```bash
cd issue1
python examples/basic_chat.py
```

## 请求结构

### 单轮对话

```python
{
    "model": "hy3-preview",
    "messages": [
        {"role": "user", "content": "请用一句话介绍腾讯混元 Hy3 模型。"}
    ],
    "temperature": 0.9,
    "top_p": 1.0,
    "max_tokens": 128
}
```

### 多轮对话

多轮对话的核心在于保留 `messages` 中的历史对话，让模型能够理解上下文：

```python
{
    "model": "hy3-preview",
    "messages": [
        {"role": "user", "content": "请用一句话介绍腾讯混元 Hy3 模型。"},
        {"role": "assistant", "content": "Hy3 是腾讯混元团队研发的..."},
        {"role": "user", "content": "那么它在代码生成方面有什么优势？请列出 3 点。"}
    ],
    "temperature": 0.7,
    "top_p": 1.0,
    "max_tokens": 256
}
```

> **关键设计**：OpenAI Chat Completions API 是无状态的。每次请求都必须携带完整的对话历史，模型不会「记住」之前的任何交互。

## 响应解析

```python
response = client.chat.completions.create(**params)
choice = response.choices[0]

# 关键字段提取
message_id = response.id                # 本次请求的唯一 ID
model_name = response.model             # 实际使用的模型名
finish_reason = choice.finish_reason    # stop / length / content_filter
content = choice.message.content        # 模型回复正文
token_usage = response.usage            # {prompt_tokens, completion_tokens, total_tokens}
```

### finish_reason 含义

| 值 | 含义 |
|:---|:---|
| `stop` | 正常结束，模型自然完成或命中 stop 序列 |
| `length` | 达到 max_tokens 上限被截断 |
| `content_filter` | 内容被安全过滤 |

## 示例输出

以下为实际调用 TokenHub `hy3-preview` 的输出：

```
=== 单轮对话 ===
模型: hy3-preview
完成原因: stop
回复: 腾讯混元 Hy3 是腾讯自研的 295B 参数混合专家大模型，以 21B 激活参数实现高效推理，在代码、数学、长文本等任务上表现优异。
Token 用量: {'prompt_tokens': 12, 'completion_tokens': 41, 'total_tokens': 53}

=== 多轮对话 ===
模型: hy3-preview
完成原因: stop
回复: Hy3 在代码生成方面具有以下优势：

1. **多语言覆盖**：支持 Python、Java、C++、Go、TypeScript 等主流语言，代码风格规范统一。
2. **上下文理解**：256K 的长上下文窗口使其能理解整个项目结构，生成与现有代码库风格一致的代码。
3. **推理驱动生成**：在复杂算法和架构设计任务中，可通过深度思考模式先分析再编码，减少逻辑错误。
Token 用量: {'prompt_tokens': 65, 'completion_tokens': 116, 'total_tokens': 181}
```

## 关键要点

1. **温度参数**：单轮开放对话推荐 `0.9`，多轮收紧至 `0.7` 以保持回答一致性
2. **Token 计数**：多轮对话的 `prompt_tokens` 随历史增长，需注意上下文预算
3. **历史管理**：生产环境中应实现滑动窗口或摘要机制，避免 messages 过长
