"""
Hy3 API - 基础对话示例 / Basic Chat Example
包含单轮对话和多轮对话
"""

from openai import OpenAI

# ============================================================
# 配置 / Configuration
# ============================================================
BASE_URL = "http://127.0.0.1:8000/v1"
API_KEY = "EMPTY"  # 自部署无需真实密钥
MODEL = "hy3"

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)


# ============================================================
# 示例 1：单轮对话 / Single-Turn Chat
# ============================================================
def single_turn_chat():
    """发送单条消息并获取回复"""
    print("=" * 60)
    print("单轮对话 / Single-Turn Chat")
    print("=" * 60)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": "用一句话解释什么是大语言模型。"},
        ],
        temperature=0.9,
        top_p=1.0,
    )

    # 解析响应
    content = response.choices[0].message.content
    finish_reason = response.choices[0].finish_reason
    usage = response.usage

    print(f"\n回复：{content}")
    print(f"\n结束原因：{finish_reason}")
    print(f"Token 用量：prompt={usage.prompt_tokens}, "
          f"completion={usage.completion_tokens}, total={usage.total_tokens}")


# ============================================================
# 示例 2：多轮对话 / Multi-Turn Chat
# ============================================================
def multi_turn_chat():
    """维护对话历史，进行多轮交互"""
    print("\n" + "=" * 60)
    print("多轮对话 / Multi-Turn Chat")
    print("=" * 60)

    # 初始化消息历史（可包含 system 提示词）
    messages = [
        {"role": "system", "content": "你是一位友好的Python编程助手。"},
    ]

    # 第一轮提问
    user_msg_1 = "Python的列表和元组有什么区别？"
    messages.append({"role": "user", "content": user_msg_1})
    print(f"\n用户：{user_msg_1}")

    response1 = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.9,
        top_p=1.0,
    )
    assistant_reply_1 = response1.choices[0].message.content
    print(f"助手：{assistant_reply_1}")

    # 将助手回复追加到历史
    messages.append({"role": "assistant", "content": assistant_reply_1})

    # 第二轮追问（基于上下文）
    user_msg_2 = "那在什么场景下应该优先使用元组？"
    messages.append({"role": "user", "content": user_msg_2})
    print(f"\n用户：{user_msg_2}")

    response2 = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.9,
        top_p=1.0,
    )
    assistant_reply_2 = response2.choices[0].message.content
    print(f"助手：{assistant_reply_2}")


# ============================================================
# 示例 3：带 System Prompt 的对话 / System Prompt Chat
# ============================================================
def system_prompt_chat():
    """使用 system prompt 控制模型行为风格"""
    print("\n" + "=" * 60)
    print("带 System Prompt 的对话 / System Prompt Chat")
    print("=" * 60)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": "你是一位资深软件架构师，回答技术问题时请先给出结论，再解释原因，最后给出代码示例。",
            },
            {"role": "user", "content": "微服务架构中，服务间通信应该选择 REST 还是 gRPC？"},
        ],
        temperature=0.9,
        top_p=1.0,
        max_tokens=1024,
    )

    print(f"\n回复：{response.choices[0].message.content}")


# ============================================================
# 运行示例
# ============================================================
if __name__ == "__main__":
    single_turn_chat()
    multi_turn_chat()
    system_prompt_chat()
