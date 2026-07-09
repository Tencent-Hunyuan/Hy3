import time
from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()
client = OpenAI(
    api_key=os.getenv("API_KEY", "EMPTY"),
    base_url=os.getenv("BASE_URL", "http://127.0.0.1:8000/v1")
)

def run_reasoning_test(question, reasoning_effort):
    start_time = time.time()

    response = client.chat.completions.create(
        model="hy3",
        messages=[
            {"role": "user", "content": question},
        ],
        temperature=0.9,
        top_p=1.0,
        extra_body = {
        "thinking": {"type": "enabled"},
        "reasoning_effort": reasoning_effort
    },
    )

    elapsed = time.time() - start_time

    return {
        "reasoning_effort": reasoning_effort,
        "content": response.choices[0].message.content,
        "time": elapsed,
        "usage": response.usage,
    }


def reasoning_mode_comparison():
    print("=== Reasoning Mode 思考过程开/关对比 ===")

    test_cases = [
        {
            "name": "简单问题",
            "question": "2+2等于多少？",
        },
        {
            "name": "数学推理",
            "question": "一个水池有两个进水管和一个出水管。单独开甲管6小时注满，单独开乙管4小时注满，单独开丙管3小时放完。现在三管同时打开，几小时可以注满水池？",
        },
        {
            "name": "逻辑推理",
            "question": "有A、B、C、D四个人，他们分别来自北京、上海、广州、深圳。已知：1) A不是北京人；2) B既不是上海人也不是北京人；3) 来自广州的不是C；4) D是深圳人。请问每个人分别来自哪里？",
        },
    ]

    for test_case in test_cases:
        print(f"\n{'='*60}")
        print(f"【测试用例】{test_case['name']}")
        print(f"问题: {test_case['question']}")
        print(f"{'='*60}")

        result_low = run_reasoning_test(test_case["question"], "low")
        time.sleep(2)
        result_high = run_reasoning_test(test_case["question"], "high")
        time.sleep(3)

        print("\n【low 模式】")
        print(f"  耗时: {result_low['time']:.4f}s")
        print(f"  Token用量: {result_low['usage'].total_tokens}")
        print(f"  回复: {result_low['content'][:200]}...")

        print("\n【high 模式】")
        print(f"  耗时: {result_high['time']:.4f}s")
        print(f"  Token用量: {result_high['usage'].total_tokens}")
        print(f"  回复: {result_high['content'][:200]}...")

        print("\n【对比分析】")
        time_diff = result_high['time'] - result_low['time']
        token_diff = result_high['usage'].total_tokens - result_low['usage'].total_tokens
        print(f"  耗时差异: +{time_diff:.4f}s")
        print(f"  Token差异: +{token_diff}")

    print(f"\n{'='*60}")
    print("【关键结论】")
    print("-" * 60)
    print("1. low (默认): 直接响应，速度快，适合简单问题")
    print("2. high: 深度思考链(CoT)，回答更准确，适合复杂推理")
    print("3. medium: 轻量思考，介于两者之间")
    print("4. 选择建议:")
    print("   - 简单问答、闲聊 → low")
    print("   - 数学计算、逻辑推理 → high")
    print("   - 需要平衡速度和准确性 → medium")


def reasoning_mode_detailed():
    print("\n\n=== Reasoning Mode 详细示例 ===")

    print("\n【完整请求参数 - high模式】")
    print(f"""
      model: hy3
      messages: [{{'role': 'user', 'content': '为什么天空是蓝色的？'}}]
      temperature: 0.9
      top_p: 1.0
      extra_body = {{
      "thinking": {{"type": "enabled"}},
      "reasoning_effort": reasoning_effort
    }},
    """)

    response = client.chat.completions.create(
        model="hy3",
        messages=[
            {"role": "user", "content": "为什么天空是蓝色的？"},
        ],
        temperature=0.9,
        top_p=1.0,
        extra_body={
            "thinking": {"type": "enabled"},
            "reasoning_effort":"high"
        },
    )

    print("\n【Response 解析】")
    print(f"  id: {response.id}")
    print(f"  model: {response.model}")
    print(f"  usage:")
    print(f"    prompt_tokens: {response.usage.prompt_tokens}")
    print(f"    completion_tokens: {response.usage.completion_tokens}")
    print(f"    total_tokens: {response.usage.total_tokens}")

    print("\n【示例输出】")
    print(f"Assistant: {response.choices[0].message.content}")


if __name__ == "__main__":
    reasoning_mode_comparison()
    reasoning_mode_detailed()