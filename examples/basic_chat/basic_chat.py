from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()
client = OpenAI(
    api_key=os.getenv("API_KEY", "EMPTY"),
    base_url=os.getenv("BASE_URL", "http://127.0.0.1:8000/v1")
)


def single_round_chat():
    print("=== 单轮对话示例 ===")

    response = client.chat.completions.create(
        model="hy3",
        messages=[
            {"role": "user", "content": "你好！请简单介绍一下你自己。"},
        ],
        temperature=0.9,
        top_p=1.0,
    )

    print("\n【完整请求参数】")
    print(f"  model: hy3")
    print(f"  messages: [{{'role': 'user', 'content': '你好！请简单介绍一下你自己。'}}]")
    print(f"  temperature: 0.9")
    print(f"  top_p: 1.0")
    print(f"  extra_body: {{'chat_template_kwargs': {{'reasoning_effort': 'no_think'}}}}")

    print("\n【完整 Response 解析】")
    print(f"  id: {response.id}")
    print(f"  object: {response.object}")
    print(f"  created: {response.created}")
    print(f"  model: {response.model}")
    print(f"  choices: {len(response.choices)} 个选择")
    print(f"  └─ 0: finish_reason = {response.choices[0].finish_reason}")
    print(f"      message:")
    print(f"        ├─ role: {response.choices[0].message.role}")
    print(f"        └─ content: {response.choices[0].message.content[:100]}...")
    print(f"  usage:")
    print(f"    ├─ prompt_tokens: {response.usage.prompt_tokens}")
    print(f"    ├─ completion_tokens: {response.usage.completion_tokens}")
    print(f"    └─ total_tokens: {response.usage.total_tokens}")

    print("\n【示例输出】")
    print(f"Assistant: {response.choices[0].message.content}")


def multi_round_chat():
    print("\n\n=== 多轮对话示例 ===")

    messages = []

    user_msg_1 = "什么是 MoE 模型？"
    messages.append({"role": "user", "content": user_msg_1})

    response_1 = client.chat.completions.create(
        model="hy3",
        messages=messages,
        temperature=0.9,
        top_p=1.0,
    )
    assistant_msg_1 = response_1.choices[0].message.content
    messages.append({"role": "assistant", "content": assistant_msg_1})

    user_msg_2 = "Hy3 在 MoE 架构上有什么创新？"
    messages.append({"role": "user", "content": user_msg_2})

    response_2 = client.chat.completions.create(
        model="hy3",
        messages=messages,
        temperature=0.9,
        top_p=1.0,
    )
    assistant_msg_2 = response_2.choices[0].message.content

    print("\n【完整对话流程】")
    for msg in messages + [{"role": "assistant", "content": assistant_msg_2}]:
        role = "User" if msg["role"] == "user" else "Assistant"
        print(f"\n{role}: {msg['content']}")

    print("\n【多轮请求的关键参数】")
    print(f"  messages 数组长度: {len(messages)}")
    print(f"  历史对话包含: {len([m for m in messages if m['role'] == 'user'])} 次用户提问")
    print(f"  最后一轮请求的 messages:")
    for i, msg in enumerate(messages):
        print(f"    [{i}] {msg['role']}: {msg['content'][:50]}...")


if __name__ == "__main__":
    single_round_chat()
    multi_round_chat()