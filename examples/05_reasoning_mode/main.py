"""
思考模式对比测试（重构版）
- 区分【思考过程】与【最终回答】
- 适配 Hy3 的 reasoning_effort 参数
"""
from openai import OpenAI
import time
import sys

client = OpenAI(
    api_key="YOUR-API-KEY",
    base_url="https://tokenhub.tencentmaas.com/v1"
)

prompt = "证明√2是无理数，要求逻辑严谨，步骤清晰"
print("=== 思考模式开/关对比测试（流式重构版） ===\n")


def test_no_reasoning():
    """关闭思考模式（流式）"""
    print("--- [模式] 关闭思考 (none) ---")
    start_time = time.time()
    first_token_time = None

    stream = client.chat.completions.create(
        model="hy3-preview",
        messages=[{"role": "user", "content": prompt}],
        extra_body={"reasoning_effort": "none"},
        temperature=0.3,
        max_tokens=2048,
        stream=True
    )

    full_response = ""
    for chunk in stream:
        if not chunk.choices:
            continue

        # 记录首Token时间
        if first_token_time is None and chunk.choices[0].delta.content:
            first_token_time = time.time()

        content = chunk.choices[0].delta.content
        if content:
            # 实时打印，不使用缓存
            print(content, end="", flush=True)
            full_response += content

    end_time = time.time()

    print("\n" + "-" * 50)
    print(f"首字耗时(TTFT): {first_token_time - start_time:.2f}s")
    print(f"总耗时: {end_time - start_time:.2f}s")
    print(f"总长度: {len(full_response)} 字符")
    print("-" * 50 + "\n")


def test_high_reasoning():
    """开启深度思考（区分思考与回答）"""
    print("--- [模式] 开启深度思考 (high) ---")
    start_time = time.time()

    stream = client.chat.completions.create(
        model="hy3-preview",
        messages=[{"role": "user", "content": prompt}],
        extra_body={"reasoning_effort": "high"},
        temperature=0.3,
        max_tokens=8192,  # 深度思考建议给足额度
        stream=True
    )

    full_reasoning = ""
    full_answer = ""

    # 用于标记是否已经进入了“回答”阶段（防止重复打印前缀）
    answer_started = False
    reasoning_started = False

    for chunk in stream:
        if not chunk.choices:
            continue

        delta = chunk.choices[0].delta

        # 1. 处理思考过程 (Hy3 特有字段)
        # 注意：有些版本的 API 可能字段名不同，常见的是 reasoning_content
        if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
            if not reasoning_started:
                print("\n[思考过程] ", end="", flush=True)
                reasoning_started = True
            content = delta.reasoning_content
            print(content, end="", flush=True)
            full_reasoning += content

        # 2. 处理最终回答
        if delta.content:
            if not answer_started:
                # 如果思考过程没打印，补一个换行
                if not reasoning_started:
                    print("\n", end="")
                print("\n[最终回答] ", end="", flush=True)
                answer_started = True
            content = delta.content
            print(content, end="", flush=True)
            full_answer += content

    end_time = time.time()

    print("\n" + "=" * 50)
    print(f"总耗时: {end_time - start_time:.2f}s")
    print(f"思考过程长度: {len(full_reasoning)} 字符")
    print(f"最终回答长度: {len(full_answer)} 字符")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    test_no_reasoning()
    test_high_reasoning()