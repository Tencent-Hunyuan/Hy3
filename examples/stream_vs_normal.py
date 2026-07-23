from openai import OpenAI
import os
import time

client = OpenAI(
    base_url="https://hy3.example.com/v1",
    api_key=os.getenv("HY3_API_KEY", "你的API_KEY")
)

prompt = "请用200字左右介绍人工智能的发展历程"

# ========== 1. 非流式请求计时 ==========
def test_non_streaming():
    start_time = time.time()
    resp = client.chat.completions.create(
        model="hy3-base",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        stream=False
    )
    total_time = time.time() - start_time
    content = resp.choices[0].message.content
    print("=== 非流式模式 ===")
    print(f"总耗时：{total_time:.2f} 秒")
    print(f"回答开头：{content[:30]}...")
    print()
    return total_time

# ========== 2. 流式请求计时（首token + 总耗时） ==========
def test_streaming():
    start_time = time.time()
    first_token_time = None
    full_content = ""

    stream = client.chat.completions.create(
        model="hy3-base",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        stream=True
    )

    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            if first_token_time is None:
                first_token_time = time.time() - start_time
            full_content += chunk.choices[0].delta.content

    total_time = time.time() - start_time
    print("=== 流式模式 ===")
    print(f"首token时延：{first_token_time:.2f} 秒")
    print(f"总耗时：{total_time:.2f} 秒")
    print(f"回答开头：{full_content[:30]}...")
    print()
    return first_token_time, total_time

if __name__ == "__main__":
    non_stream_total = test_non_streaming()
    first_token, stream_total = test_streaming()

    print("=== 对比总结 ===")
    print(f"非流式总耗时：{non_stream_total:.2f}s")
    print(f"流式首token时延：{first_token:.2f}s（用户更快看到第一个字）")
    print(f"流式总耗时：{stream_total:.2f}s")
