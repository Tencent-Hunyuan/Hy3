"""Hy3 流式请求与逐 chunk 解析示例。"""

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


def load_project_env() -> None:
    candidates = [Path.cwd() / ".env", Path.cwd() / "quickstart" / ".env"]
    if "__file__" in globals():
        candidates.insert(0, Path(__file__).resolve().parents[2] / ".env")
    for candidate in candidates:
        if candidate.is_file():
            load_dotenv(candidate, override=False)
            return


load_project_env()

BASE_URL = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.getenv("HY3_API_KEY", "EMPTY")
MODEL = os.getenv("HY3_MODEL", "hy3")
MAX_TOKENS = int(os.getenv("HY3_MAX_TOKENS", "128"))
REASONING_EFFORT = os.getenv("HY3_REASONING_EFFORT", "no_think")


def main() -> None:
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
    stream = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": "请用三句话说明流式响应适合什么场景。",
            }
        ],
        temperature=0.9,
        top_p=1.0,
        max_tokens=MAX_TOKENS,
        stream=True,
        stream_options={"include_usage": True},
        extra_body={
            "chat_template_kwargs": {
                "reasoning_effort": REASONING_EFFORT,
            }
        },
    )

    text_by_choice: dict[int, list[str]] = {}
    finish_reasons: dict[int, str] = {}
    response_id = None
    response_model = None
    usage = None

    for chunk_number, chunk in enumerate(stream, start=1):
        response_id = response_id or chunk.id
        response_model = response_model or chunk.model
        usage = getattr(chunk, "usage", None) or usage

        # usage chunk 可能没有 choices，因此必须遍历而不是固定访问 choices[0]。
        for choice in chunk.choices:
            index = choice.index
            delta = choice.delta
            text_by_choice.setdefault(index, [])

            role = getattr(delta, "role", None)
            content = getattr(delta, "content", None)
            reasoning = getattr(delta, "reasoning_content", None)

            print(
                f"chunk={chunk_number}, choice={index}, "
                f"role={role!r}, content={content!r}, "
                f"finish_reason={choice.finish_reason!r}"
            )
            if reasoning:
                print(f"  reasoning_content={reasoning!r}")
            if content:
                text_by_choice[index].append(content)
            if choice.finish_reason:
                finish_reasons[index] = choice.finish_reason

    print("\n=== 重建后的完整响应 ===")
    print(f"id={response_id}")
    print(f"model={response_model}")
    for index in sorted(text_by_choice):
        print(f"choice[{index}].finish_reason={finish_reasons.get(index)}")
        print(f"choice[{index}].content={''.join(text_by_choice[index])}")
    if usage:
        print(
            "usage: "
            f"prompt={usage.prompt_tokens}, "
            f"completion={usage.completion_tokens}, "
            f"total={usage.total_tokens}"
        )
    else:
        print("usage=当前服务未在流式响应中返回 usage")


if __name__ == "__main__":
    main()
