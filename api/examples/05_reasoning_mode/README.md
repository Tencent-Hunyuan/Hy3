# 05 - Reasoning Mode（思考模式）

演示思考过程开启与关闭的对比。

## 说明

Hy3 支持通过 `reasoning_effort` 参数控制思考深度。关闭思考时模型直接给出答案；开启深度思考后，模型会先生成内部思维链（Chain-of-Thought），再输出最终答案。

## 运行方式

```bash
pip install openai python-dotenv
cp ../../.env.example ../../.env  # 编辑 .env 填入密钥
python reasoning_mode.py
```

## 代码

```python
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("HY3_API_KEY", "EMPTY"),
    base_url=os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
)

messages = [
    {"role": "user", "content": "一个水池有一个进水管和一个出水管。单开进水管 3 小时注满，单开出水管 5 小时排空。如果同时打开，多久能注满？"}
]

# 关闭思考
response_no_think = client.chat.completions.create(
    model="hy3",
    messages=messages,
    temperature=0.9,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)
print(f"[no_think]\n{response_no_think.choices[0].message.content}\n")

# 开启深度思考
response_high = client.chat.completions.create(
    model="hy3",
    messages=messages,
    temperature=0.9,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}},
)
msg = response_high.choices[0].message
if hasattr(msg, "reasoning_content") and msg.reasoning_content:
    print(f"[reasoning_content]\n{msg.reasoning_content}\n")
print(f"[high thinking]\n{msg.content}\n")
```

### 示例输出

**no_think（直接回复）**：
```
同时打开进水管和出水管，每小时净注水 1/3 - 1/5 = 2/15，需要 7.5 小时注满。
```

**high（深度思考）**：
```
思考过程：这是一个经典的进出水问题。进水管速率 = 1/3 池/小时，
出水管速率 = 1/5 池/小时。同时打开时净速率 = 1/3 - 1/5 = 5/15 - 3/15 = 2/15 池/小时。
所以时间 = 1 / (2/15) = 7.5 小时。

最终答案：7.5 小时。
```

---

完整源码：[reasoning_mode.py](./reasoning_mode.py)
