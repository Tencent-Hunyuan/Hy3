from openai import OpenAI
from dotenv import load_dotenv
import os
import time

load_dotenv()

client = OpenAI(
    api_key=os.getenv("HY3_API_KEY"),
    base_url="https://tokenhub.tencentmaas.com/v1",
)

messages = [
    {"role": "user", "content": "请详细介绍一下腾讯混元大模型的主要特点和应用场景。"},
]

def compare_streaming_performance():
    print("=== 性能对比测试 ===")
    print("测试问题:", messages[0]["content"])
    print()

    print("1. 非流式请求（stream: false）")
    start_time = time.time()
    response = client.chat.completions.create(
        model="hy3",
        messages=messages,
        stream=False,
    )
    end_time = time.time()
    total_time_non_stream = end_time - start_time
    content_length = len(response.choices[0].message.content)

    print(f"   总耗时: {total_time_non_stream:.2f} 秒")
    print(f"   响应长度: {content_length} 字符")
    print(f"   输出速度: {content_length / total_time_non_stream:.1f} 字符/秒")
    print()

    print("2. 流式请求（stream: true）")
    start_time = time.time()
    first_token_received = False
    first_token_time = 0
    full_content = ""

    stream = client.chat.completions.create(
        model="hy3",
        messages=messages,
        stream=True,
        stream_options={"include_usage": True},
    )

    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            if not first_token_received:
                first_token_time = time.time()
                first_token_received = True
            full_content += chunk.choices[0].delta.content

    end_time = time.time()
    total_time_stream = end_time - start_time
    ttft = first_token_time - start_time
    content_length_stream = len(full_content)

    print(f"   首 token 时延 (TTFT): {ttft:.2f} 秒")
    print(f"   总耗时: {total_time_stream:.2f} 秒")
    print(f"   响应长度: {content_length_stream} 字符")
    print(f"   输出速度: {content_length_stream / total_time_stream:.1f} 字符/秒")
    print()

    print("=== 对比结果 ===")
    print(f"{'指标':<20} {'非流式':<15} {'流式':<15}")
    print(f"{'首 token 时延':<20} {'N/A':<15} {f'{ttft:.2f} 秒':<15}")
    print(f"{'总耗时':<20} {f'{total_time_non_stream:.2f} 秒':<15} {f'{total_time_stream:.2f} 秒':<15}")
    print(f"{'输出速度':<20} {f'{content_length / total_time_non_stream:.1f} 字符/秒':<15} {f'{content_length_stream / total_time_stream:.1f} 字符/秒':<15}")

if __name__ == "__main__":
    compare_streaming_performance()