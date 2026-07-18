# Basic Chat（单轮 / 多轮）

## 目标

本示例演示如何通过 Hy3 的 OpenAI 兼容 Chat Completions API 完成单轮对话，以及如何把上一轮 assistant 回复加入 `messages` 后继续多轮对话。

## 前置条件

- Python 3.10+
- OpenAI Python SDK `openai>=1.0.0`，环境变量加载库 `python-dotenv>=1.0.0`
- 环境变量：`HY3_BASE_URL`、`HY3_API_KEY`、`HY3_MODEL`；可从 `quickstart/.env.example` 复制为 `quickstart/.env`
- 模型能力要求：支持 Chat Completions 与多轮文本对话

安装依赖：

```bash
python -m pip install "openai>=1.0.0" "python-dotenv>=1.0.0"
```

## 完整请求

```python
messages = [
    {"role": "system", "content": "你是一个简洁、准确的中文助手。"},
    {"role": "user", "content": "请用一句话介绍 Hy3。"},
]

first_response = client.chat.completions.create(
    model=MODEL,
    messages=messages,
    temperature=0.9,
    top_p=1.0,
    max_tokens=128,
    extra_body={
        "chat_template_kwargs": {"reasoning_effort": "no_think"}
    },
)

first_answer = first_response.choices[0].message.content or ""
messages.extend(
    [
        {"role": "assistant", "content": first_answer},
        {"role": "user", "content": "请把刚才的介绍改写成三个要点。"},
    ]
)
second_response = client.chat.completions.create(
    model=MODEL,
    messages=messages,
    temperature=0.9,
    top_p=1.0,
    max_tokens=128,
    extra_body={
        "chat_template_kwargs": {"reasoning_effort": "no_think"}
    },
)
```

## 完整 Response 解析

脚本会遍历全部 `choices`，解析响应 ID、模型、创建时间、角色、正文、结束原因和 Token 用量。多轮对话必须把第一轮的 assistant 正文原样加入下一次请求，而不是只发送第二条用户消息。

```python
print(response.id, response.model, response.created)
for choice in response.choices:
    print(choice.index)
    print(choice.message.role)
    print(choice.message.content)
    print(choice.finish_reason)

if response.usage:
    print(response.usage.prompt_tokens)
    print(response.usage.completion_tokens)
    print(response.usage.total_tokens)
```

## 运行方式

在 `quickstart/` 目录执行：

```bash
python examples/01_basic_chat/basic_chat.py
```

## 示例输出

以下内容仅展示输出结构，回答文本、ID 和 Token 数会随部署与生成结果变化。

```text
=== 单轮对话 ===
id=chatcmpl-example-1
model=hy3
choice[0].role=assistant
choice[0].finish_reason=stop
choice[0].content=Hy3 是腾讯混元团队研发的混合专家大语言模型。
usage: prompt=25, completion=18, total=43

=== 多轮对话（第 2 轮） ===
id=chatcmpl-example-2
model=hy3
choice[0].role=assistant
choice[0].finish_reason=stop
choice[0].content=1. 混合专家架构。\n2. 支持长上下文。\n3. 支持推理与工具调用。
usage: prompt=58, completion=35, total=93
```
