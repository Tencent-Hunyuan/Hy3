from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(
    api_key=os.getenv("HY3_API_KEY"),
    base_url="https://tokenhub.tencentmaas.com/v1",
)

def basic_single_turn():
    print("=== 单轮对话示例 ===")
    response = client.chat.completions.create(
        model="hy3",
        messages=[
            {"role": "user", "content": "你好，请简单介绍一下你自己。"},
        ],
        temperature=0.9,
    )

    print("=== 响应内容 ===")
    print("ID:", response.id)
    print("模型:", response.model)
    print("回答:", response.choices[0].message.content)
    print("结束原因:", response.choices[0].finish_reason)
    print("\n=== Token 使用 ===")
    print(f"输入: {response.usage.prompt_tokens} tokens")
    print(f"输出: {response.usage.completion_tokens} tokens")
    print(f"总计: {response.usage.total_tokens} tokens")

def basic_multi_turn():
    print("\n=== 多轮对话示例 ===")
    messages = []

    user_msg = "你好，我是morning，请简单介绍一下你自己。"
    messages.append({"role": "user", "content": user_msg})

    response = client.chat.completions.create(
        model="hy3",
        messages=messages,
        temperature=0.9,
    )

    assistant_reply = response.choices[0].message.content
    messages.append({"role": "assistant", "content": assistant_reply})
    print(f"用户: {user_msg}")
    print(f"助手: {assistant_reply}")
    print()

    user_msg = "你擅长什么？"
    messages.append({"role": "user", "content": user_msg})

    response = client.chat.completions.create(
        model="hy3",
        messages=messages,
        temperature=0.9,
    )

    assistant_reply = response.choices[0].message.content
    messages.append({"role": "assistant", "content": assistant_reply})
    print(f"用户: {user_msg}")
    print(f"助手: {assistant_reply}")
    print()

    user_msg = "那你能帮我写一段 Python 代码吗？"
    messages.append({"role": "user", "content": user_msg})

    response = client.chat.completions.create(
        model="hy3",
        messages=messages,
        temperature=0.9,
    )

    assistant_reply = response.choices[0].message.content
    messages.append({"role": "assistant", "content": assistant_reply})
    print(f"用户: {user_msg}")
    print(f"助手: {assistant_reply}")

    user_msg = "你还记得我叫什么吗？"
    messages.append({"role": "user", "content": user_msg})

    response = client.chat.completions.create(
        model="hy3",
        messages=messages,
        temperature=0.9,
    )

    assistant_reply = response.choices[0].message.content
    print(f"用户: {user_msg}")
    print(f"助手: {assistant_reply}")

if __name__ == "__main__":
    basic_single_turn()
    basic_multi_turn()