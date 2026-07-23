from openai import OpenAI
import os

# 初始化客户端
client = OpenAI(
    base_url="https://hy3.example.com/v1",
    api_key=os.getenv("HY3_API_KEY", "你的API_KEY")
)

# ========== 1. 单轮对话示例 ==========
def single_turn_chat():
    print("=== 单轮对话 ===")
    response = client.chat.completions.create(
        model="hy3-base",
        messages=[
            {"role": "user", "content": "请用一句话介绍一下Hy3模型"}
        ],
        temperature=0.7,
        max_tokens=200
    )
    # 解析返回结果
    answer = response.choices[0].message.content
    print("用户：请用一句话介绍一下Hy3模型")
    print("助手：", answer)
    print()
    return answer

# ========== 2. 多轮对话示例 ==========
def multi_turn_chat():
    print("=== 多轮对话 ===")
    # 历史消息列表，多轮需要保留上下文
    messages = [
        {"role": "user", "content": "你好，我想学习Python"},
        {"role": "assistant", "content": "你好！学习Python可以从基础语法开始，比如变量、循环、函数这些知识点。"},
        {"role": "user", "content": "那第一步应该学什么？"}
    ]

    response = client.chat.completions.create(
        model="hy3-base",
        messages=messages,
        temperature=0.7,
        max_tokens=300
    )

    answer = response.choices[0].message.content
    print("历史对话：")
    for msg in messages:
        print(f"{msg['role']}: {msg['content']}")
    print("assistant:", answer)
    print()

if __name__ == "__main__":
    single_turn_chat()
    multi_turn_chat()
