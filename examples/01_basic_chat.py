"""01 basic chat: single-turn and multi-turn conversation."""
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
    base_url=os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
)
MODEL = os.environ.get("HY3_MODEL", "hy3")


def single_turn():
    print("=== single-turn ===")
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "用一句话介绍你自己"}],
        temperature=0.9,
        top_p=1.0,
        max_tokens=128,
    )
    msg = resp.choices[0].message
    print("assistant:", msg.content)
    print("usage:", getattr(resp, "usage", None))
    return resp


def multi_turn():
    print("\n=== multi-turn ===")
    messages = [
        {"role": "system", "content": "你是简洁的中文助手。"},
        {"role": "user", "content": "我叫小明，请记住。"},
    ]
    r1 = client.chat.completions.create(
        model=MODEL, messages=messages, max_tokens=64, temperature=0.9
    )
    a1 = r1.choices[0].message.content
    print("assistant-1:", a1)
    messages.append({"role": "assistant", "content": a1 or ""})
    messages.append({"role": "user", "content": "我叫什么名字？"})
    r2 = client.chat.completions.create(
        model=MODEL, messages=messages, max_tokens=64, temperature=0.9
    )
    print("assistant-2:", r2.choices[0].message.content)
    return r2


if __name__ == "__main__":
    single_turn()
    multi_turn()
