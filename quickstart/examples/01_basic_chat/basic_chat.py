"""Hy3 单轮与多轮基础对话示例。"""

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


def load_project_env() -> None:
    """从 quickstart/.env 或当前目录加载环境变量。"""
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
TEMPERATURE = float(os.getenv("HY3_TEMPERATURE", "0.9"))
TOP_P = float(os.getenv("HY3_TOP_P", "1.0"))
MAX_TOKENS = int(os.getenv("HY3_MAX_TOKENS", "128"))
REASONING_EFFORT = os.getenv("HY3_REASONING_EFFORT", "no_think")


def create_completion(client: OpenAI, messages: list[dict[str, str]]):
    """发送一次完整的非流式 Chat Completions 请求。"""
    return client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=TEMPERATURE,
        top_p=TOP_P,
        max_tokens=MAX_TOKENS,
        extra_body={
            "chat_template_kwargs": {
                "reasoning_effort": REASONING_EFFORT,
            }
        },
    )


def parse_response(label: str, response) -> str:
    """解析响应元数据、全部 choices 和 token usage。"""
    print(f"\n=== {label} ===")
    print(f"id={response.id}")
    print(f"model={response.model}")
    print(f"created={response.created}")

    for choice in response.choices:
        message = choice.message
        print(f"choice[{choice.index}].role={message.role}")
        print(f"choice[{choice.index}].finish_reason={choice.finish_reason}")
        print(f"choice[{choice.index}].content={message.content}")
        if message.tool_calls:
            print(f"choice[{choice.index}].tool_calls={message.tool_calls}")

    if response.usage:
        print(
            "usage: "
            f"prompt={response.usage.prompt_tokens}, "
            f"completion={response.usage.completion_tokens}, "
            f"total={response.usage.total_tokens}"
        )

    return response.choices[0].message.content or ""


def main() -> None:
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

    # 单轮对话：一条用户消息对应一次回复。
    messages = [
        {"role": "system", "content": "你是一个简洁、准确的中文助手。"},
        {"role": "user", "content": "请用一句话介绍 Hy3。"},
    ]
    first_response = create_completion(client, messages)
    first_answer = parse_response("单轮对话", first_response)

    # 多轮对话：把上一轮 assistant 回复与新的 user 消息一起传回。
    messages.extend(
        [
            {"role": "assistant", "content": first_answer},
            {"role": "user", "content": "请把刚才的介绍改写成三个要点。"},
        ]
    )
    second_response = create_completion(client, messages)
    parse_response("多轮对话（第 2 轮）", second_response)


if __name__ == "__main__":
    main()
