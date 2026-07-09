"""
Hy3 思考模式（Reasoning Mode）对比示例
=====================================

演示通过 reasoning_effort 切换 Hy3 的思考深度，对比两种模式：
  - no_think：直接响应，不进行链式思考（适合日常对话，默认）
  - high    ：深度链式思考，适合数学/代码/复杂推理任务

reasoning_effort 通过 extra_body={"chat_template_kwargs": {"reasoning_effort": ...}} 传入。
开启思考时，响应可能在 message.reasoning_content 字段中返回思维链（CoT），
最终答案在 message.content 中。reasoning_content 是否独立分离取决于服务端
是否启用了 reasoning 解析器（vLLM: --reasoning-parser hy_v3；SGLang: --reasoning-parser hunyuan）。

连接信息通过环境变量配置（带默认值）：
  HY3_BASE_URL  默认 http://127.0.0.1:8000/v1
  HY3_API_KEY   默认 EMPTY
"""

import os

from openai import OpenAI

# 通过环境变量初始化客户端（带默认值），方便切换部署地址
client = OpenAI(
    base_url=os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
    api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
)

MODEL = "hy3"

# 适合触发推理的提示词：带简单数学运算的逐步分析题
PROMPT = "小明有 5 个苹果，分给 3 个朋友每人 1 个，又买了 2 个，现在他还有几个苹果？请逐步分析。"


def chat(reasoning_effort: str):
    """以指定 reasoning_effort 调用 Hy3，返回完整 message 对象。"""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT}],
        temperature=0.9,
        top_p=1.0,
        extra_body={
            "chat_template_kwargs": {"reasoning_effort": reasoning_effort}
        },
    )
    return response.choices[0].message


def print_section(title, message):
    """统一打印某次调用的 reasoning_content（如有）与 content。"""
    print("=" * 70)
    print(title)
    print("=" * 70)
    print(f"【用户提问】\n{PROMPT}\n")

    # reasoning_content 是可选字段：服务端启用 reasoning 解析器后才会分离出来
    reasoning_content = getattr(message, "reasoning_content", None)
    if reasoning_content:
        print("【思维链 reasoning_content】")
        print(reasoning_content)
        print()
    else:
        print("【思维链 reasoning_content】(无，未分离或该模式不产生思考内容)\n")

    print("【最终回答 content】")
    print(message.content)
    print()


def main():
    # ---- 调用 1：no_think，直接响应 ----
    msg_no_think = chat("no_think")
    print_section("模式一：reasoning_effort = no_think（直接响应）", msg_no_think)

    # ---- 调用 2：high，深度链式思考 ----
    msg_high = chat("high")
    print_section("模式二：reasoning_effort = high（深度思考）", msg_high)

    # ---- 对比小结 ----
    print("=" * 70)
    print("【对比小结】")
    print("=" * 70)
    print("no_think：直接给出答案，无思维链，响应快，适合日常对话。")
    print("high    ：先输出逐步推理（reasoning_content），再给最终答案，")
    print("          适合数学/代码/复杂逻辑推理任务。")
    print()
    print("提示：若 reasoning_content 始终为空，请确认服务端启用了 reasoning 解析器：")
    print("  vLLM:   --reasoning-parser hy_v3")
    print("  SGLang: --reasoning-parser hunyuan")


if __name__ == "__main__":
    main()
