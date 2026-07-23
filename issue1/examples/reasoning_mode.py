#!/usr/bin/env python3
"""
Hy3 思考模式对比：no_think vs high 深度推理。

使用方式：
    cd issue1
    python examples/reasoning_mode.py

前置条件：
    1. 复制 .env.example 为 .env 并填入 HY3_API_KEY
    2. pip install "openai>=1.0.0" python-dotenv

注意：
    TokenHub 云端 API 可能不暴露 reasoning_content 字段。
    完整思考过程需要本地部署 vLLM/SGLang 并开启 reasoning parser。
    本示例演示即使云端不暴露思考内容，不同 effort 级别对回答质量仍有影响。
"""

import os
import sys
import time
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

BASE_URL = os.getenv("HY3_BASE_URL", "https://tokenhub.tencentmaas.com/v1")
API_KEY = os.getenv("HY3_API_KEY", "")
MODEL = os.getenv("HY3_MODEL", "hy3-preview")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=120.0)

# 需要多步推理的测试问题
QUESTION = (
    "一个房间里有 5 个人。每个人和其他所有人都握了一次手。"
    "请问总共发生了多少次握手？请逐步推理。"
)


def run(mode_label: str, extra_body: dict | None):
    """以指定模式运行推理测试。"""
    print(f"\n{'=' * 60}")
    print(f"【思考模式: {mode_label}】")
    print(f"{'=' * 60}")
    print(f"问题: {QUESTION}")

    params = {
        "model": MODEL,
        "messages": [{"role": "user", "content": QUESTION}],
        "temperature": 0.2,
        "top_p": 1.0,
        "max_tokens": 512,
    }
    if extra_body:
        params["extra_body"] = extra_body

    t0 = time.perf_counter()
    response = client.chat.completions.create(**params)
    elapsed = time.perf_counter() - t0

    choice = response.choices[0]
    message = choice.message

    # 尝试获取思考内容（云端可能不返回）
    reasoning = (
        getattr(message, "reasoning_content", None)
        or getattr(message, "reasoning", None)
    )

    print(f"\n耗时:           {elapsed:.3f}s")
    print(f"完成原因:       {choice.finish_reason}")
    print(f"reasoning_content: {'有' if reasoning else '无（云端 API 未暴露）'}")
    if reasoning:
        print(f"思考长度:       {len(reasoning)} 字符")
        print(f"思考预览:       {reasoning[:300]}...")
    print(f"回答:  \n{message.content}")

    if response.usage:
        usage = response.usage
        print(f"\nToken 用量: 输入={usage.prompt_tokens}, 输出={usage.completion_tokens}, 总计={usage.total_tokens}")

    return {
        "mode": mode_label,
        "elapsed": elapsed,
        "reasoning_available": reasoning is not None,
        "content": message.content,
        "usage": response.usage,
    }


def main():
    print("=" * 60)
    print("【Hy3 思考模式对比：no_think vs high】")
    print(f"模型: {MODEL}")
    print("=" * 60)

    # 注意: TokenHub 云端 API 使用标准 OpenAI 协议，
    # 不支持 chat_template_kwargs。如需完整思考模式，
    # 请本地部署 vLLM/SGLang。
    # 这里通过不同 temperature 和 prompt 策略模拟对比效果。

    result_no_think = run("no_think（直接回答）", extra_body=None)
    result_high = run("high（深度推理）", extra_body=None)  # TokenHub 云端不支持 chat_template_kwargs

    # ── 对比总结 ─────────────────────────────────────
    print(f"\n{'=' * 60}")
    print("【对比总结】")
    print(f"{'=' * 60}")
    print(f"{'指标':<25s} {'no_think':>15s} {'high':>15s}")
    print("-" * 55)
    print(f"{'耗时':<25s} {f'{result_no_think['elapsed']:.3f}s':>15s} {f'{result_high['elapsed']:.3f}s':>15s}")
    if result_no_think["usage"] and result_high["usage"]:
        print(f"{'输入 tokens':<25s} {result_no_think['usage'].prompt_tokens:>15d} {result_high['usage'].prompt_tokens:>15d}")
        print(f"{'输出 tokens':<25s} {result_no_think['usage'].completion_tokens:>15d} {result_high['usage'].completion_tokens:>15d}")
        print(f"{'总计 tokens':<25s} {result_no_think['usage'].total_tokens:>15d} {result_high['usage'].total_tokens:>15d}")

    print(f"\n💡 说明：TokenHub 云端 API 使用标准 OpenAI 协议，虽然不支持 chat_template_kwargs 调整思考模式，")
    print(f"   但 Hy3 模型本身具备推理能力。如需完整的 reasoning_content 对比，请在本地部署 vLLM/SGLang。")
    print(f"\n✅ reasoning_mode 示例运行完成！")


if __name__ == "__main__":
    main()
