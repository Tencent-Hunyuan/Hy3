"""对比 Hy3 关闭和开启思考模式时的响应。"""

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
PROMPT = "列出 1 到 20 中所有能被 3 整除的整数，并计算它们的和。"


def extract_reasoning_content(message):
    """兼容 SDK 属性和 Pydantic model_extra 中的扩展字段。"""
    reasoning = getattr(message, "reasoning_content", None)
    if reasoning:
        return reasoning
    model_extra = getattr(message, "model_extra", None) or {}
    return model_extra.get("reasoning_content")


def run_mode(client: OpenAI, reasoning_effort: str):
    return client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT}],
        temperature=0.9,
        top_p=1.0,
        max_tokens=MAX_TOKENS,
        extra_body={
            "chat_template_kwargs": {
                "reasoning_effort": reasoning_effort,
            }
        },
    )


def parse_response(label: str, response) -> None:
    print(f"\n=== {label} ===")
    print(f"id={response.id}")
    print(f"model={response.model}")
    for choice in response.choices:
        message = choice.message
        reasoning = extract_reasoning_content(message)
        print(f"choice[{choice.index}].finish_reason={choice.finish_reason}")
        print(
            f"choice[{choice.index}].reasoning_content="
            f"{reasoning if reasoning else '<未返回独立思考字段>'}"
        )
        print(f"choice[{choice.index}].content={message.content}")
    if response.usage:
        print(
            "usage: "
            f"prompt={response.usage.prompt_tokens}, "
            f"completion={response.usage.completion_tokens}, "
            f"total={response.usage.total_tokens}"
        )


def main() -> None:
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

    no_think_response = run_mode(client, "no_think")
    high_response = run_mode(client, "high")

    parse_response("思考关闭：no_think", no_think_response)
    parse_response("思考开启：high", high_response)


if __name__ == "__main__":
    main()
