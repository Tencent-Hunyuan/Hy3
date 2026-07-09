#### `basic_chat.py` (基础对话)
#### **说明**

展示单轮和多轮对话，多轮对话需维护历史消息列表。

```
# 基础对话示例：单轮与多轮对话

本示例展示如何使用 Hy3 API 进行单轮和多轮对话，重点在于维护对话历史消息。

## 使用说明
1. 将代码中的 `[YOUR_API_KEY]` 替换为有效密钥。
2. 运行 `python basic_chat.py` 查看结果。

## 示例内容
- 单轮对话：直接发送用户消息，获取回复。
- 多轮对话：通过维护 `messages` 列表保留上下文。

## 关键点
- 多轮对话需将历史消息（`system`、`user`、`assistant` 角色）传递给模型。
- 模型基于完整上下文生成连贯回复。
```

**代码块 (**`**basic_chat.py)**`

```python
from openai import OpenAI

client = OpenAI(api_key="YOUR_API_KEY", base_url="https://api.hunyuan.cloud.tencent.com/v1")

# 单轮对话示例
response_single = client.chat.completions.create(
    model="hunyuan-turbo",
    messages=[{"role": "user", "content": "你好，你是谁？"}]
)
print("单轮对话回复：")
print(response_single.choices[0].message.content)

# 多轮对话示例
messages = [
    {"role": "system", "content": "你是一个助手，需要友好回答问题。"},
    {"role": "user", "content": "今天天气怎么样？"},
    {"role": "assistant", "content": "天气晴，气温 25℃。"},
    {"role": "user", "content": "适合出门吗？"}
]
response_multi = client.chat.completions.create(model="hunyuan-turbo", messages=messages)
print("多轮对话回复：")
print(response_multi.choices[0].message.content)
```

**示例输出**

```
单轮对话回复：你好！我是 Hy3 助手，很高兴为你解答问题。
多轮对话回复：非常适合，天气晴朗且温度适宜，建议带上防晒用品出门。
```



