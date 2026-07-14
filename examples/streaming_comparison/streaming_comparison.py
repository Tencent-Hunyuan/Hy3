from openai import OpenAI
import time
import os
from dotenv import load_dotenv
load_dotenv()
client = OpenAI(
    api_key=os.getenv("API_KEY", "EMPTY"),
    base_url=os.getenv("BASE_URL", "http://127.0.0.1:8000/v1")
)


def non_streaming_request():
    print("=== 非流式请求 ===")

    start_time = time.time()

    response = client.chat.completions.create(
        model="hy3",
        messages=[
            {"role": "user", "content": "请详细解释什么是人工智能大模型，包括其工作原理、主要特点和应用场景"},
        ],
        temperature=0.9,
        top_p=1.0,
    )

    total_time = time.time() - start_time
    content = response.choices[0].message.content

    return {
        "total_time": total_time,
        "first_token_time": total_time,
        "content_length": len(content),
        "content": content,
        "usage": response.usage,
    }


def streaming_request():
    print("\n=== 流式请求 ===")

    start_time = time.time()
    first_token_time = None

    stream = client.chat.completions.create(
        model="hy3",
        messages=[
            {"role": "user", "content": "请详细解释什么是人工智能大模型，包括其工作原理、主要特点和应用场景"},
        ],
        temperature=0.9,
        top_p=1.0,
        stream=True,
    )

    full_content = ""

    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            if first_token_time is None:
                first_token_time = time.time() - start_time
            full_content += chunk.choices[0].delta.content

    total_time = time.time() - start_time

    return {
        "total_time": total_time,
        "first_token_time": first_token_time or total_time,
        "content_length": len(full_content),
        "content": full_content,
    }


def run_comparison():
    print("=== Non-Streaming vs Streaming 对比测试 ===")
    print("\n测试问题: 请详细解释什么是人工智能大模型")
    print("=" * 60)

    non_stream_result = non_streaming_request()
    stream_result = streaming_request()

    print("\n" + "=" * 60)
    print("【性能对比结果】")
    print("-" * 60)
    print(f"{'指标':<25} {'非流式':<15} {'流式':<15}")
    print("-" * 60)
    print(f"{'首 Token 时延 (TTFT)':<25} {non_stream_result['first_token_time']:.4f}s {stream_result['first_token_time']:.4f}s")
    print(f"{'总耗时 (Total Time)':<25} {non_stream_result['total_time']:.4f}s {stream_result['total_time']:.4f}s")
    print(f"{'内容长度':<25} {non_stream_result['content_length']:<15} {stream_result['content_length']:<15}")
    print("-" * 60)

    ttft_improvement = ((non_stream_result['first_token_time'] - stream_result['first_token_time']) / non_stream_result['first_token_time']) * 100
    print(f"\n首 Token 时延提升: {ttft_improvement:.1f}%")

    print("\n【示例输出（截断）】")
    print("\n非流式回复:")
    print(f"  {non_stream_result['content'][:150]}...")
    print("\n流式回复:")
    print(f"  {stream_result['content'][:150]}...")

    print("\n【关键结论】")
    print("1. 非流式: 需要等待完整响应生成后才能获取结果")
    print("2. 流式: 可以快速获取第一个 token，提升用户体验")
    print("3. 首 Token 时延是流式最大优势，适合实时对话场景")
    print("4. 总耗时两者相近，但流式能让用户更早看到内容")


if __name__ == "__main__":
    run_comparison()