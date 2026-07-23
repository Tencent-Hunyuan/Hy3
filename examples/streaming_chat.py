from openai import OpenAI
import os

client = OpenAI(
    base_url="https://hy3.example.com/v1",
    api_key=os.getenv("HY3_API_KEY", "你的API_KEY")
)

def streaming_chat_demo():
    print("=== 流式逐块输出示例 ===")
    print("用户：请简单介绍一下大语言模型的流式输出")
    print("助手：", end="", flush=True)

    # 开启流式请求 stream=True
    stream = client.chat.completions.create(
        model="hy3-base",
        messages=[
            {"role": "user", "content": "请简单介绍一下大语言模型的流式输出"}
        ],
        temperature=0.7,
        max_tokens=300,
        stream=True
    )

    full_answer = ""
    # 逐 chunk 解析并打印
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            content = chunk.choices[0].delta.content
            full_answer += content
            print(content, end="", flush=True)

    print("\n")
    print("=== 完整拼接后的回答 ===")
    print(full_answer)

if __name__ == "__main__":
    streaming_chat_demo()
