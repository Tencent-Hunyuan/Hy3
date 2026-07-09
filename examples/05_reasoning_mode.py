"""
Hy3 思考模式（Reasoning Mode）对比示例
=====================================

演示通过 thinking 开关切换 Hy3 的思考模式，对比两种模式：
  - 思考关闭：直接响应，不进行链式思考（适合日常对话）
  - 思考开启：深度链式思考，适合数学/代码/复杂推理任务

思考模式开关的传参方式因部署方式而异，本示例同时发送两种参数以兼容：
  - 云端 TokenHub API：extra_body={"thinking": {"type": "enabled"|"disabled"}}
  - 本地 vLLM/SGLang 部署：extra_body={"chat_template_kwargs": {"reasoning_effort": "high"|"no_think"}}

开启思考时，响应在 message.reasoning_content 字段返回思维链（CoT），
最终答案在 message.content 中。
  - 云端：reasoning_content 由 TokenHub API 自动分离
  - 本地：需服务端启用 reasoning 解析器（vLLM: --reasoning-parser hy_v3；SGLang: --reasoning-parser hunyuan）

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


def chat(enable_thinking: bool):
    """以指定思考模式调用 Hy3，返回完整 message 对象。

    同时发送 thinking（云端 TokenHub）与 chat_template_kwargs.reasoning_effort
    （本地 vLLM/SGLang）两套参数，实现本地/云端兼容：
      - 云端识别 thinking，本地忽略该字段
      - 本地识别 chat_template_kwargs.reasoning_effort，云端忽略该字段
    """
    thinking_type = "enabled" if enable_thinking else "disabled"
    reasoning_effort = "high" if enable_thinking else "no_think"
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT}],
        temperature=0.9,
        top_p=1.0,
        extra_body={
            # 云端 TokenHub API 的思考开关
            "thinking": {"type": thinking_type},
            # 本地 vLLM/SGLang 部署的思考深度开关
            "chat_template_kwargs": {"reasoning_effort": reasoning_effort},
        },
    )
    return response.choices[0].message


def print_section(title, message):
    """统一打印某次调用的 reasoning_content（如有）与 content。"""
    print("=" * 70)
    print(title)
    print("=" * 70)
    print(f"【用户提问】\n{PROMPT}\n")

    # reasoning_content 是可选字段：思考开启时返回思维链
    reasoning_content = getattr(message, "reasoning_content", None)
    if reasoning_content:
        print("【思维链 reasoning_content】")
        print(reasoning_content)
        print()
    else:
        print("【思维链 reasoning_content】(无，思考关闭或服务端未启用 reasoning 解析器)\n")

    print("【最终回答 content】")
    print(message.content)
    print()


def main():
    # ---- 调用 1：思考关闭，直接响应 ----
    msg_off = chat(enable_thinking=False)
    print_section("模式一：思考关闭（thinking: disabled / reasoning_effort: no_think）", msg_off)

    # ---- 调用 2：思考开启，深度链式思考 ----
    msg_on = chat(enable_thinking=True)
    print_section("模式二：思考开启（thinking: enabled / reasoning_effort: high）", msg_on)

    # ---- 对比小结 ----
    print("=" * 70)
    print("【对比小结】")
    print("=" * 70)
    print("思考关闭：直接给出答案，无思维链，响应快，适合日常对话。")
    print("思考开启：先输出逐步推理（reasoning_content），再给最终答案，")
    print("          适合数学/代码/复杂逻辑推理任务。")
    print()
    print("提示：若思考开启时 reasoning_content 仍为空，请确认：")
    print("  - 云端 TokenHub API：使用 thinking 参数（本示例已包含）")
    print("  - 本地 vLLM:   启动时加 --reasoning-parser hy_v3")
    print("  - 本地 SGLang: 启动时加 --reasoning-parser hunyuan")


if __name__ == "__main__":
    main()
