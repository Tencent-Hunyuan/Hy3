from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(
    api_key=os.getenv("HY3_API_KEY"),
    base_url="https://tokenhub.tencentmaas.com/v1",
)

def reasoning_mode_comparison():
    messages = [
        {"role": "user", "content": "小明有5个苹果，给了小红2个，又买了3个，最后还剩几个？"},
    ]

    print("=== 思考模式对比 ===")
    print("问题:", messages[0]["content"])
    print()

    print("1. 关闭思考模式（thinking: disabled）")
    response = client.chat.completions.create(
        model="hy3",
        messages=messages,
        extra_body={"thinking": {"type": "disabled"}},
    )

    msg = response.choices[0].message
    print("回答:", msg.content)
    if hasattr(msg, "reasoning_content"):
        print("思考过程:", getattr(msg, "reasoning_content"))
    else:
        print("思考过程: 无（思考模式已关闭）")
    print(f"Token 消耗: {response.usage.total_tokens}")
    print()

    print("2. 开启思考模式（thinking: enabled）")
    response = client.chat.completions.create(
        model="hy3",
        messages=messages,
        extra_body={"thinking": {"type": "enabled"}},
    )

    msg = response.choices[0].message
    print("回答:", msg.content)
    if hasattr(msg, "reasoning_content"):
        print("思考过程:", getattr(msg, "reasoning_content"))
    print(f"Token 消耗: {response.usage.total_tokens}")

def reasoning_effort_comparison():
    messages = [
        {"role": "user", "content": "请详细分析一下为什么天空是蓝色的。"},
    ]

    print("\n=== 推理深度对比 ===")
    print("问题:", messages[0]["content"])
    print()

    for effort in ["low", "medium", "high"]:
        print(f"{effort} 推理深度")
        response = client.chat.completions.create(
            model="hy3",
            messages=messages,
            extra_body={"reasoning_effort": effort},
        )
        
        msg = response.choices[0].message
        print("回答:", msg.content[:100], "..." if len(msg.content) > 100 else "")
        if hasattr(msg, "reasoning_content"):
            reasoning = getattr(msg, "reasoning_content")
            print("思考过程:", reasoning[:80], "..." if len(reasoning) > 80 else "")
        print(f"Token 消耗: {response.usage.total_tokens}")
        print()

if __name__ == "__main__":
    reasoning_mode_comparison()
    reasoning_effort_comparison()