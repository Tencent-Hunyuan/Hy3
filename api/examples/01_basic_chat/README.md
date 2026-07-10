# 01 - Basic Chat（基础对话）

演示单轮与多轮对话。

## 运行方式

```bash
# 安装依赖
pip install openai python-dotenv

# 配置环境变量
cp ../../.env.example ../../.env
# 编辑 .env 文件填入你的 API 密钥和地址

# 运行
python basic_chat.py
```

## 单轮对话

```python
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("HY3_API_KEY", "EMPTY"),
    base_url=os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
)

response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "用一句话解释什么是量子计算。"},
    ],
    temperature=0.9,
    top_p=1.0,
)

print(response.choices[0].message.content)
```

### 示例输出

```
量子计算是利用量子力学原理（如叠加和纠缠）进行信息处理的新型计算范式，
在处理某些特定问题时相比经典计算机具有指数级的速度优势。
```

### Response 结构解析

```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1719000000,
  "model": "hy3",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "量子计算是..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 15,
    "completion_tokens": 42,
    "total_tokens": 57
  }
}
```

## 多轮对话

```python
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_API_KEY",
    base_url="https://tokenhub.tencentmaas.com/v1",
)

messages = [
    {"role": "user", "content": "推荐几本科幻小说。"},
]

# 第一轮
response = client.chat.completions.create(
    model="hy3", messages=messages, temperature=0.9,
)
assistant_reply = response.choices[0].message.content
print(f"Assistant: {assistant_reply}\n")
messages.append({"role": "assistant", "content": assistant_reply})

# 第二轮：追问
messages.append({"role": "user", "content": "我最喜欢《三体》，能再推荐类似的作品吗？"})
response = client.chat.completions.create(
    model="hy3", messages=messages, temperature=0.9,
)
print(f"Assistant: {response.choices[0].message.content}")
```

### 示例输出

```
Assistant: 推荐：《三体》（刘慈欣）、《银河帝国》（阿西莫夫）、《沙丘》（赫伯特）...

Assistant: 喜欢《三体》的话，可以试试《盲视》（彼得·沃茨），同样是硬核科幻，
探讨意识与智能的关系。还有《深渊上的火》（弗诺·文奇），宇宙尺度的宏大叙事。
```

---

完整源码：[basic_chat.py](./basic_chat.py)
