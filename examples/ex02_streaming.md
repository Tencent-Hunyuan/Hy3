# 02 Streaming：流式请求与逐 chunk 解析

流式返回（`stream=True`）可以在模型生成第一个 token 时就开始输出，适合聊天 UI、长文本生成等场景。本示例演示如何发起流式请求并正确拼接 chunk。

## 完整请求

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("HY3_API_KEY"),
    base_url="https://tokenhub.tencentmaas.com/v1",
)

response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "请写一首关于人工智能的短诗。"},
    ],
    temperature=0.8,
    max_tokens=512,
    stream=True,
)

print("=== 流式输出 ===")
full_content = ""
for chunk in response:
    choice = chunk.choices[0]
    delta = choice.delta

    # 流式中 content 增量可能为 None
    if delta and delta.content:
        full_content += delta.content
        print(delta.content, end="", flush=True)

    # 判断流式结束
    if choice.finish_reason:
        print(f"\n[finish_reason: {choice.finish_reason}]")

print("\n=== 拼接后的完整内容 ===")
print(full_content)
```

## Response 解析

流式响应中，每个 chunk 的 `choices[0].delta` 只包含增量内容：

- `delta.content`：本次 chunk 新增的文本；第一个 chunk 可能只有 role，content 为空。
- `delta.reasoning_content`：若开启思考模式，会额外返回推理过程增量。
- `choices[0].finish_reason`：流结束时为 `stop`、`length` 或 `content_filter`。

## 示例输出

```text
=== 流式输出 ===
代码编织梦境，
数据点亮星河，
硅基之心学会思考，
在比特间轻舞飞扬。
[finish_reason: stop]

=== 拼接后的完整内容 ===
代码编织梦境，
数据点亮星河，
硅基之心学会思考，
在比特间轻舞飞扬。
```

## 要点提示

1. 必须遍历整个 generator，否则连接可能提前关闭。
2. 开启思考模式时，注意区分 `delta.reasoning_content` 与 `delta.content`。
3. 流式请求不要通过 `response.choices[0].message.content` 读取完整内容，需要手动拼接。
