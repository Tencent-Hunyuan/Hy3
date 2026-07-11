from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(
    api_key=os.getenv("HY3_API_KEY"),
    base_url="https://tokenhub.tencentmaas.com/v1",
)

def streaming_chat():
    print("=== 流式请求示例 ===")
    stream = client.chat.completions.create(
        model="hy3",
        messages=[
            {"role": "user", "content": "请写一段关于人工智能发展的简短介绍。"},
        ],
        stream=True,
        stream_options={"include_usage": True},
    )

    print("\n=== 流式输出 ===")
    full_content = ""
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            content = chunk.choices[0].delta.content
            full_content += content
            print(content, end="", flush=True)
        if chunk.usage:
            print("\n\n=== Token 使用 ===")
            print(f"输入: {chunk.usage.prompt_tokens} tokens")
            print(f"输出: {chunk.usage.completion_tokens} tokens")
            print(f"总计: {chunk.usage.total_tokens} tokens")

    print("\n\n=== 完整响应 ===")
    print(full_content)

if __name__ == "__main__":
    streaming_chat()