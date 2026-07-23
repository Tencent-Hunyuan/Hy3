from openai import OpenAI
import os

client = OpenAI(
    base_url="https://hy3.example.com/v1",
    api_key=os.getenv("HY3_API_KEY", "你的API_KEY")
)

question = "有一个水池，单开甲管6小时注满，单开乙管4小时注满。两管同时开，几小时能注满水池？"

# ========== 1. 关闭思考模式（直接出答案） ==========
def reasoning_off():
    print("=== 思考模式关闭 ===")
    resp = client.chat.completions.create(
        model="hy3-base",
        messages=[{"role": "user", "content": question}],
        max_tokens=300,
        reasoning_mode=False
    )
    answer = resp.choices[0].message.content
    print("回答：")
    print(answer)
    print()

# ========== 2. 开启思考模式（展示推理过程） ==========
def reasoning_on():
    print("=== 思考模式开启 ===")
    resp = client.chat.completions.create(
        model="hy3-reason",
        messages=[{"role": "user", "content": question}],
        max_tokens=800,
        reasoning_mode=True
    )
    message = resp.choices[0].message
    # 思考过程与最终回答分离
    reasoning_content = message.reasoning_content if hasattr(message, "reasoning_content") else "（无思考过程输出）"
    final_answer = message.content

    print("思考过程：")
    print(reasoning_content)
    print("\n最终答案：")
    print(final_answer)
    print()

if __name__ == "__main__":
    reasoning_off()
    reasoning_on()
    print("=== 对比总结 ===")
    print("关闭思考：回答简洁、速度快，适合日常对话")
    print("开启思考：输出完整推理步骤，准确率更高，适合数学、逻辑类复杂问题")
