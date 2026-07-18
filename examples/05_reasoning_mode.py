"""05 reasoning mode: no_think vs high effort."""
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
    base_url=os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
)
MODEL = os.environ.get("HY3_MODEL", "hy3")
PROMPT = "一个班级有 30 人，其中 18 人喜欢数学，20 人喜欢英语，至少有多少人两门都喜欢？请给出答案与简要推理。"


def call_with_effort(effort: str):
    # 兼容本地 chat_template_kwargs 与部分云端 thinking 字段
    extra = {
        "chat_template_kwargs": {"reasoning_effort": effort},
        "thinking": {"type": "enabled" if effort != "no_think" else "disabled"},
    }
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT}],
        max_tokens=512,
        temperature=0.3,
        extra_body=extra,
    )
    msg = resp.choices[0].message
    reasoning = getattr(msg, "reasoning_content", None)
    if reasoning is None and isinstance(msg.model_extra, dict):
        reasoning = msg.model_extra.get("reasoning_content")
    return {
        "effort": effort,
        "content": msg.content,
        "reasoning_content": reasoning,
    }


if __name__ == "__main__":
    for effort in ("no_think", "high"):
        print(f"=== reasoning_effort={effort} ===")
        out = call_with_effort(effort)
        print("content:", out["content"])
        print("reasoning_content:", out["reasoning_content"])
        print()
