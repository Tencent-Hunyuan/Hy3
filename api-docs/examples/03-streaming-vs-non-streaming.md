# Example 03: Non-Streaming vs Streaming

对比非流式与流式请求的**首 token 时延（TTFT）**和**总耗时**差异。

---

## 为什么需要对比？

| 指标 | 非流式 | 流式 |
|:---|:---|:---|
| **首 token 时延（TTFT）** | 不可感知（必须等全部生成完毕） | 可精确测量 |
| **用户体感** | 等待期间无反馈（"白屏"） | 逐字输出，即时反馈 |
| **总耗时** | 生成时间 = 总耗时 | 与生成时间基本一致 |
| **适用场景** | 后台批处理、结构化输出 | 交互式对话、实时 UI |

---

## 环境准备

```bash
pip install openai
```

---

## 对比测试

### 完整代码

```python
import os
import time
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("HY3_API_KEY", "YOUR_API_KEY"),
    base_url="https://tokenhub.tencentmaas.com/v1",
)

PROMPT = "请用中文详细介绍 Python 的异步编程模型，大约 300 字"

# ============================================================
# 公共参数
# ============================================================
common_params = {
    "model": "hy3",
    "messages": [{"role": "user", "content": PROMPT}],
    "temperature": 0.9,
    "max_tokens": 512,
}


# ============================================================
# 测试 1: 非流式
# ============================================================
def test_non_streaming():
    print("=" * 60)
    print("【非流式请求】")
    print("=" * 60)

    start = time.time()
    response = client.chat.completions.create(**common_params, stream=False)
    total_time = time.time() - start

    content = response.choices[0].message.content
    usage = response.usage

    print(f"  总耗时:           {total_time:.2f}s")
    print(f"  首 token 时延:    N/A（非流式不可测）")
    print(f"  prompt_tokens:     {usage.prompt_tokens}")
    print(f"  completion_tokens: {usage.completion_tokens}")
    print(f"  回复字数:         {len(content)} 字符")
    print()

    return {
        "mode": "non-streaming",
        "total_time": total_time,
        "ttft": None,
        "completion_tokens": usage.completion_tokens,
        "content": content,
    }


# ============================================================
# 测试 2: 流式
# ============================================================
def test_streaming():
    print("=" * 60)
    print("【流式请求】")
    print("=" * 60)

    start = time.time()
    stream = client.chat.completions.create(**common_params, stream=True)

    collected = ""
    ttft = None
    chunk_count = 0
    final_usage = None

    for chunk in stream:
        chunk_count += 1
        if not chunk.choices:
            continue

        delta = chunk.choices[0].delta

        if delta and delta.content:
            if ttft is None:
                ttft = time.time() - start
            collected += delta.content

        if hasattr(chunk, "usage") and chunk.usage:
            final_usage = chunk.usage

    total_time = time.time() - start

    print(f"  总耗时:              {total_time:.2f}s")
    print(f"  首 token 时延 (TTFT): {ttft:.3f}s" if ttft else "  首 token 时延 (TTFT): N/A")
    print(f"  chunk 数:            {chunk_count}")
    if final_usage:
        print(f"  prompt_tokens:        {final_usage.prompt_tokens}")
        print(f"  completion_tokens:    {final_usage.completion_tokens}")
    print(f"  回复字数:            {len(collected)} 字符")
    print()

    return {
        "mode": "streaming",
        "total_time": total_time,
        "ttft": ttft,
        "completion_tokens": final_usage.completion_tokens if final_usage else None,
        "content": collected,
    }


# ============================================================
# 执行对比
# ============================================================
if __name__ == "__main__":

    client.chat.completions.create(
        model="hy3",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=10,
    )

    # 开始测试
    r1 = test_non_streaming()
    r2 = test_streaming()

    # ============================================================
    # 对比汇总
    # ============================================================
    print("=" * 60)
    print("【对比汇总】")
    print("=" * 60)
    print(f"  {'指标':<25s} {'非流式':>12s} {'流式':>12s}")
    print(f"  {'-'*45}")
    print(f"  {'总耗时':<25s} {r1['total_time']:>11.2f}s {r2['total_time']:>11.2f}s")
    if r2["ttft"]:
        print(f"  {'首 token 时延 (TTFT)':<25s} {'N/A':>12s} {r2['ttft']:>11.3f}s")
    print(f"  {'用户首次感知耗时':<25s} {r1['total_time']:>11.2f}s {r2['ttft']:>11.3f}s")
    print()

    # 解读
    if r2["ttft"]:
        improvement = (1 - r2["ttft"] / r1["total_time"]) * 100
        print(f"  💡 流式模式下，用户在 {r2['ttft']:.3f}s 即可看到首个 token，")
        print(f"     比非流式快 {improvement:.0f}%（用户体感层面的加速）。")
        print(f"     总生成时间两者基本一致（取决于模型推理速度）。")

```

### 示例输出

============================================================
【非流式请求】
============================================================
  总耗时:           4.04s
  首 token 时延:    N/A（非流式不可测）
  prompt_tokens:     29
  completion_tokens: 183
  回复字数:         343 字符

============================================================
【流式请求】
============================================================
  总耗时:              4.83s
  首 token 时延 (TTFT): 0.625s
  chunk 数:            129
  回复字数:            495 字符

============================================================
【对比汇总】
============================================================
  指标                                 非流式           流式
  ---------------------------------------------
  总耗时                              4.04s        4.83s
  首 token 时延 (TTFT)                  N/A       0.625s
  用户首次感知耗时                         4.04s       0.625s