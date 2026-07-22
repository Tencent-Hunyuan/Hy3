"""
对应Issue要求：basic chat（单轮/多轮对话示例）
包含：完整请求参数、响应解析、示例输出
"""
from openai import OpenAI

# 初始化Hy3客户端
client = OpenAI(
    api_key="YOUR_API_KEY",
    base_url="https://tokenhub.tencentmaas.com/v1"
)

def test_single_turn():
    """单轮对话：无历史上下文"""
    print("=== 单轮对话测试 ===")
    response = client.chat.completions.create(
        model="hy3-preview",
        messages=[
            {"role": "user", "content": "用3句话介绍腾讯混元大模型"}
        ],
        temperature=0.7,
        max_tokens=200
    )
    # 解析完整响应
    content = response.choices[0].message.content
    usage = response.usage
    print(f"模型回复：{content}")
    print(f"Token消耗：输入{usage.prompt_tokens}，输出{usage.completion_tokens}，总{usage.total_tokens}\n")

def test_multi_turn():
    """多轮对话：保留历史上下文"""
    print("=== 多轮对话测试 ===")
    messages = [
        {"role": "system", "content": "你是一个擅长科普的AI助手"},
        {"role": "user", "content": "什么是大模型微调？"}
    ]
    # 第一轮请求
    response1 = client.chat.completions.create(
        model="hy3-preview",
        messages=messages,
        temperature=0.7
    )
    reply1 = response1.choices[0].message.content
    print(f"用户问：什么是大模型微调？")
    print(f"模型答：{reply1}\n")
    
    # 追加历史消息，发起第二轮请求
    messages.append({"role": "assistant", "content": reply1})
    messages.append({"role": "user", "content": "微调和大模型预训练有什么区别？"})
    
    response2 = client.chat.completions.create(
        model="hy3-preview",
        messages=messages,
        temperature=0.7
    )
    print(f"用户问：微调和大模型预训练有什么区别？")
    print(f"模型答：{response2.choices[0].message.content}")

if __name__ == "__main__":
    test_single_turn()
    test_multi_turn()