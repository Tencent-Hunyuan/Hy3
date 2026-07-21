"""示例 01：basic_chat 基础对话（单轮 & 多轮）

运行:
    python 01_basic_chat.py
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# 初始化客户端
# 用户：HY3_API_KEY 处填写密钥，HY3_BASE_URL 填 /v1 地址
# 本地部署：api_key="EMPTY"，base_url  "http://127.0.0.1:8000/v1" 地址
client = OpenAI(
    api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
    base_url=os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
    timeout=int(os.environ.get("HY3_TIMEOUT_SECONDS", "60")),
)
MODEL = os.environ.get("HY3_MODEL", "hy3")

# 基础对话推荐使用 no_think, 速度上最快
REASONING = {"chat_template_kwargs": {"reasoning_effort": "no_think"}}


def main() -> None:
    
    # 单轮对话
    
    print("=== 单轮对话 ===")
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": "用一句话解释什么是 API。"},
        ],
        temperature=0.9,
        top_p=1.0,
        max_tokens=256,
        extra_body=REASONING,
    )

    message = response.choices[0].message
    print("回答:", message.content)
    print("结束原因:", response.choices[0].finish_reason)
    print("Token 用量:", response.usage)

    # 多轮对话

    print("\n=== 多轮对话 ===")
    messages = [
        {"role": "system", "content": "你是一个简洁、准确的编程助手。"},
        {"role": "user", "content": "Python 列表推导式是什么？"},
    ]

    # 第一轮
    r1 = client.chat.completions.create(
        model=MODEL, messages=messages, temperature=0.3, max_tokens=256, extra_body=REASONING,
    )
    print("助手:", r1.choices[0].message.content)

    # 把 assistant 回复加入历史，再追问
    messages.append({"role": "assistant", "content": r1.choices[0].message.content})
    messages.append({"role": "user", "content": "给一个只保留偶数的例子。"})

    # 第二轮
    r2 = client.chat.completions.create(
        model=MODEL, messages=messages, temperature=0.3, max_tokens=256, extra_body=REASONING,
    )
    print("助手:", r2.choices[0].message.content)


if __name__ == "__main__":
    main()
