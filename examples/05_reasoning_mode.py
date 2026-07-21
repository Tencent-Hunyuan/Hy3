"""示例 05：思考模式对比（no_think / low / high）

开启后，响应里会多一个 reasoning_content 字段，包含模型的内部推理过程

控制方式：
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think" | "low" | "high"}}

本示例对比 no_think（直接回复）与 high（深度思考链）的差异。

运行:
    python 05_reasoning_mode.py
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
    base_url=os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
    timeout=int(os.environ.get("HY3_TIMEOUT_SECONDS", "60")),
)
MODEL = os.environ.get("HY3_MODEL", "hy3")

# 使用简单数学题演示
QUESTION = "一个笼子里有鸡和兔共 35 只，脚共 94 只，问鸡和兔各几只？"


def ask(effort: str) -> None:
    """用指定 reasoning_effort 提问，打印思考过程和最终答案。"""
    print(f"\n{'='*50}")
    print(f"reasoning_effort = {effort}")
    print(f"{'='*50}")

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": QUESTION}],
        temperature=0.3,
        max_tokens=int(os.environ.get("HY3_REASONING_MAX_TOKENS", "4096")),
        extra_body={"chat_template_kwargs": {"reasoning_effort": effort}},
    )
    msg = response.choices[0].message

    # reasoning_content: 模型的内部思考
    # 服务端未启用 reasoning parser 时该字段不存在，用 getattr 安全读取
    rc = getattr(msg, "reasoning_content", None)
    if rc:
        print(f"[思考过程] (前 300 字)\n{rc[:300]}{'...' if len(rc) > 300 else ''}")
    else:
        print("[思考过程] (无：no_think 模式不输出推理，或 reasoning parser 未启用)")

    print(f"\n[最终答案]\n{msg.content}")
    print(f"[Token 用量] {response.usage}")


def main() -> None:
    ask("no_think")   # 关闭思考：直接回复
    ask("high")       # 深度思考：先推理再回答


if __name__ == "__main__":
    main()
