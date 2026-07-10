# 03 - Non-streaming vs Streaming（非流式 vs 流式对比）

比较非流式与流式请求的首 token 时延和总耗时。

## 说明

| 模式 | 首 token 时延 | 总耗时 | 适用场景 |
|------|---------------|--------|---------|
| Non-streaming | 高（等待完整响应） | 低（一次接收） | 无需实时展示，如后台处理 |
| Streaming | 低（边生成边接收） | 相近 | 需要实时展示给用户 |

## 运行方式

```bash
pip install openai python-dotenv
cp ../../.env.example ../../.env  # 编辑 .env 填入密钥
python nonstreaming_vs_streaming.py
```

## 代码

```python
import time
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("HY3_API_KEY", "EMPTY"),
    base_url=os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
)

messages = [
    {"role": "user", "content": "请详细解释机器学习中的 Transformer 架构，包括自注意力机制的原理。"},
]

# ===== Non-streaming =====
start = time.time()
response = client.chat.completions.create(
    model="hy3", messages=messages, temperature=0.9,
)
non_streaming_total = time.time() - start
non_streaming_content = response.choices[0].message.content
print(f"[Non-streaming] 总耗时: {non_streaming_total:.2f}s")
print(f"[Non-streaming] 输出长度: {len(non_streaming_content)} 字符")

# ===== Streaming =====
start = time.time()
first_token_time = None
stream = client.chat.completions.create(
    model="hy3", messages=messages,
    stream=True, temperature=0.9,
)
streaming_content = ""
for chunk in stream:
    if first_token_time is None and chunk.choices[0].delta.content:
        first_token_time = time.time() - start
    delta = chunk.choices[0].delta
    if delta.content:
        streaming_content += delta.content

streaming_total = time.time() - start
print(f"[Streaming] 首 token 时延: {first_token_time:.2f}s")
print(f"[Streaming] 总耗时: {streaming_total:.2f}s")
print(f"[Streaming] 输出长度: {len(streaming_content)} 字符")
```

### 示例输出

```
[Non-streaming] 总耗时: 8.35s
[Non-streaming] 输出长度: 1842 字符

[Streaming] 首 token 时延: 1.82s
[Streaming] 总耗时: 8.41s
[Streaming] 输出长度: 1842 字符
```

可以看到流式模式的首 token 时延显著低于非流式模式，总耗时才相近。

---

完整源码：[nonstreaming_vs_streaming.py](./nonstreaming_vs_streaming.py)
