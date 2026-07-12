# 03 Non-streaming vs Streaming：首 token 时延与总耗时

本示例对比非流式与流式请求的首 token 时延（TTFT, Time To First Token）与总耗时，帮助你在 latency 敏感场景选择合适的调用方式。

## 完整请求

```python
import os
import time
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("HY3_API_KEY"),
    base_url="https://tokenhub.tencentmaas.com/v1",
)

PROMPT = "请用 300 字左右解释机器学习中的梯度下降算法。"


def measure_non_streaming():
    start = time.perf_counter()
    response = client.chat.completions.create(
        model="hy3",
        messages=[{"role": "user", "content": PROMPT}],
        temperature=0.7,
        max_tokens=512,
        stream=False,
    )
    end = time.perf_counter()

    content = response.choices[0].message.content
    print("=== 非流式 ===")
    print(f"首 token 时延: {end - start:.3f}s (非流式需等全部生成完才能拿到结果)")
    print(f"总耗时: {end - start:.3f}s")
    print(f"输出长度: {len(content)} 字符")
    print(content[:200] + "...")
    return end - start


def measure_streaming():
    start = time.perf_counter()
    first_token_time = None
    response = client.chat.completions.create(
        model="hy3",
        messages=[{"role": "user", "content": PROMPT}],
        temperature=0.7,
        max_tokens=512,
        stream=True,
    )

    full_content = ""
    for chunk in response:
        delta = chunk.choices[0].delta
        if delta and delta.content:
            if first_token_time is None:
                first_token_time = time.perf_counter()
            full_content += delta.content

    end = time.perf_counter()

    print("\n=== 流式 ===")
    print(f"首 token 时延 (TTFT): {first_token_time - start:.3f}s")
    print(f"总耗时: {end - start:.3f}s")
    print(f"输出长度: {len(full_content)} 字符")
    print(full_content[:200] + "...")
    return end - start


non_stream_total = measure_non_streaming()
stream_total = measure_streaming()

print(f"\n对比：非流式总耗时 {non_stream_total:.3f}s，流式总耗时 {stream_total:.3f}s")
```

## Response 解析

- **非流式**：请求在模型生成完整回复后才返回，因此“首 token 时延”等于“总耗时”。
- **流式**：首 chunk 到达时即可开始输出，TTFT 通常远小于总耗时，能显著改善用户体验。

> 注意：流式与非流式的总 token 生成时间通常相近，差异主要在于“何时开始收到内容”。

## 示例输出

```text
=== 非流式 ===
首 token 时延: 2.345s (非流式需等全部生成完才能拿到结果)
总耗时: 2.345s
输出长度: 312 字符
梯度下降是一种常用的优化算法，它通过不断调整模型参数来最小化损失函数...

=== 流式 ===
首 token 时延 (TTFT): 0.412s
总耗时: 2.298s
输出长度: 312 字符
梯度下降是一种常用的优化算法，它通过不断调整模型参数来最小化损失函数...

对比：非流式总耗时 2.345s，流式总耗时 2.298s
```

## 要点提示

1. 对实时性要求高的场景（如聊天 UI）优先使用流式。
2. 只需要完整结果的后端任务（如批量处理）可使用非流式，代码更简单。
3. 测量 TTFT 时应排除网络握手时间，多次采样取平均值更准确。
