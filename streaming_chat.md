#### `streaming_chat.py` **(流式输出)**

通过流式请求实时获取模型生成的文本，模拟打字机效果。

```
# 流式对话示例：逐字符接收模型输出

本示例演示如何通过流式请求实时获取模型生成的文本，模拟打字机效果。

## 使用说明
1. 替换 `[YOUR_API_KEY]`。
2. 运行 `python streaming_chat.py`，观察逐字符输出。

## 关键点
- 设置 `stream=True` 启用流式响应。
- 通过迭代 `response` 对象获取实时生成的文本块。
- 使用 `chunk.choices[0].delta.content` 获取增量内容。
```

**代码块 (**`**streaming_chat.py)**`

```python
from openai import OpenAI

client = OpenAI(api_key="YOUR_API_KEY", base_url="https://tokenhub.tencentmaas.com/v1")

response = client.chat.completions.create(
    model="hunyuan-turbo",
    messages=[{"role": "user", "content": "讲个笑话。"}],
    stream=True
)

print("流式输出：", end="")
for chunk in response:
    if chunk.choices[0].delta.content is not None:
        print(chunk.choices[0].delta.content, end="", flush=True)
print("\n流式结束。")
```

**示例输出**

```
流式输出：小明问大师：“大师，你能算出我什么时候能发财吗？” 大师掐指一算，缓缓说道：“你在三十岁的时候会黄袍加身，每日都有大鱼大肉为伴。” 小明听了特别高兴，满心期待着三十岁的到来。终于，小明三十岁了，他成为了一名美团外卖骑手。流式结束。
```

