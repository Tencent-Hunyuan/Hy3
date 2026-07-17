"""
Hy3 API - 思考模式示例 / Reasoning Mode Example
对比 no_think / low / high 三种思考模式
"""

import time
from openai import OpenAI

# ============================================================
# 配置 / Configuration
# ============================================================
BASE_URL = "http://127.0.0.1:8000/v1"
API_KEY = "EMPTY"
MODEL = "hy3"

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

# 测试问题（数学应用题，适合展示思考能力）
MATH_PROMPT = (
    "一个水池有A、B两个进水管。A管单独注满需要6小时，"
    "B管单独注满需要8小时。同时打开两管，需要多少小时注满？"
)

COMPLEX_PROMPT = "证明根号2是无理数。"


# ============================================================
# 辅助函数 / Helper
# ============================================================
def request_with_reasoning_effort(prompt: str, effort: str) -> tuple:
    """发送请求并返回（耗时, 回复内容, 思考过程）"""
    t0 = time.time()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
        top_p=1.0,
        extra_body={"chat_template_kwargs": {"reasoning_effort": effort}},
    )
    elapsed = time.time() - t0

    msg = response.choices[0].message
    content = msg.content
    reasoning = getattr(msg, "reasoning_content", None)

    return elapsed, content, reasoning


# ============================================================
# 示例 1：no_think 模式 / No Thinking
# ============================================================
def demo_no_think():
    """no_think：直接输出结果，不展示思考过程"""
    print("=" * 60)
    print(f"no_think 模式")
    print("=" * 60)
    print(f"问题：{MATH_PROMPT}\n")

    elapsed, content, _ = request_with_reasoning_effort(MATH_PROMPT, "no_think")

    print(f"回复（{elapsed:.2f}s）：")
    print(content)


# ============================================================
# 示例 2：high 模式 / Deep Reasoning
# ============================================================
def demo_high():
    """high：展示完整深度思维链"""
    print("\n" + "=" * 60)
    print("high 模式（深度思考）")
    print("=" * 60)
    print(f"问题：{MATH_PROMPT}\n")

    elapsed, content, reasoning = request_with_reasoning_effort(MATH_PROMPT, "high")

    if reasoning:
        print(f"思考过程（{elapsed:.2f}s）：")
        print(reasoning)
        print("\n最终答案：")
    else:
        print(f"回复（{elapsed:.2f}s）：")

    print(content)


# ============================================================
# 示例 3：复杂推理任务 / Complex Reasoning Task
# ============================================================
def demo_complex_reasoning():
    """在复杂任务上对比 no_think 和 high"""
    print("\n" + "=" * 60)
    print("复杂推理任务对比")
    print("=" * 60)
    print(f"问题：{COMPLEX_PROMPT}\n")

    # no_think
    time_nt, content_nt, _ = request_with_reasoning_effort(COMPLEX_PROMPT, "no_think")
    print(f"--- no_think ({time_nt:.2f}s) ---")
    print(content_nt[:300] + "..." if len(content_nt) > 300 else content_nt)

    # high
    print()
    time_h, content_h, reasoning_h = request_with_reasoning_effort(COMPLEX_PROMPT, "high")

    if reasoning_h:
        print(f"--- high - 思考过程 ({time_h:.2f}s) ---")
        print(reasoning_h[:300] + "..." if len(reasoning_h) > 300 else reasoning_h)
        print("\n--- high - 最终答案 ---")
    else:
        print(f"--- high ({time_h:.2f}s) ---")

    print(content_h[:300] + "..." if len(content_h) > 300 else content_h)


# ============================================================
# 示例 4：时延对比汇总 / Latency Comparison Summary
# ============================================================
def latency_comparison():
    """汇总三种模式的时延对比"""
    print("\n" + "=" * 60)
    print("时延对比汇总 / Latency Comparison Summary")
    print("=" * 60)

    prompt = "计算 123 × 456 × 789"
    efforts = ["no_think", "low", "high"]
    results = {}

    for effort in efforts:
        try:
            elapsed, content, reasoning = request_with_reasoning_effort(prompt, effort)
            results[effort] = {
                "time": elapsed,
                "content_len": len(content),
                "reasoning_len": len(reasoning) if reasoning else 0,
            }
        except Exception as e:
            print(f"  {effort}: 请求失败 - {e}")

    print(f"\n问题：{prompt}")
    print(f"\n{'模式':<15} {'耗时':>10} {'回复长度':>12} {'思考长度':>12}")
    print("-" * 52)
    for effort, data in results.items():
        print(f"{effort:<15} {data['time']:>8.2f}s {data['content_len']:>10} {data['reasoning_len']:>10}")

    print("\n建议：")
    print("  - 简单任务 → no_think（最低延迟）")
    print("  - 中等任务 → low（平衡延迟与解释性）")
    print("  - 复杂任务 → high（最高准确率，展示完整思维链）")


# ============================================================
# 运行示例
# ============================================================
if __name__ == "__main__":
    demo_no_think()
    demo_high()
    demo_complex_reasoning()
    latency_comparison()
