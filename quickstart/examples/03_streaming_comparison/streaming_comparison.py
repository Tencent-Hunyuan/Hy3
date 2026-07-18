"""比较 Hy3 非流式与流式请求的首个可见内容时延和总耗时。"""

import os
import time
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
PROMPT = "请用五个要点解释大语言模型的流式输出。"


def common_request() -> dict:
    return {
        "model": MODEL,
        "messages": [{"role": "user", "content": PROMPT}],
        "temperature": 0.9,
        "top_p": 1.0,
        "max_tokens": MAX_TOKENS,
        "extra_body": {
            "chat_template_kwargs": {
                "reasoning_effort": REASONING_EFFORT,
            }
        },
    }


def run_non_streaming(client: OpenAI) -> dict:
    started_at = time.perf_counter()
    response = client.chat.completions.create(**common_request())
    total_seconds = time.perf_counter() - started_at

    choices = []
    for choice in response.choices:
        choices.append(
            {
                "index": choice.index,
                "finish_reason": choice.finish_reason,
                "content": choice.message.content or "",
            }
        )

    usage = None
    if response.usage:
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

    return {
        "id": response.id,
        "model": response.model,
        "choices": choices,
        "usage": usage,
        # 非流式接口在响应完成前不会向客户端暴露 token。
        "first_visible_seconds": total_seconds,
        "total_seconds": total_seconds,
    }


def run_streaming(client: OpenAI) -> dict:
    started_at = time.perf_counter()
    first_content_seconds = None
    response_id = None
    response_model = None
    chunk_count = 0
    text_by_choice: dict[int, list[str]] = {}
    finish_reasons: dict[int, str] = {}
    usage = None

    stream = client.chat.completions.create(
        **common_request(),
        stream=True,
        stream_options={"include_usage": True},
    )
    for chunk in stream:
        chunk_count += 1
        response_id = response_id or chunk.id
        response_model = response_model or chunk.model
        chunk_usage = getattr(chunk, "usage", None)
        if chunk_usage:
            usage = {
                "prompt_tokens": chunk_usage.prompt_tokens,
                "completion_tokens": chunk_usage.completion_tokens,
                "total_tokens": chunk_usage.total_tokens,
            }

        for choice in chunk.choices:
            text_by_choice.setdefault(choice.index, [])
            content = getattr(choice.delta, "content", None)
            if content:
                if first_content_seconds is None:
                    first_content_seconds = time.perf_counter() - started_at
                text_by_choice[choice.index].append(content)
            if choice.finish_reason:
                finish_reasons[choice.index] = choice.finish_reason

    total_seconds = time.perf_counter() - started_at
    choices = [
        {
            "index": index,
            "finish_reason": finish_reasons.get(index),
            "content": "".join(text_by_choice[index]),
        }
        for index in sorted(text_by_choice)
    ]
    return {
        "id": response_id,
        "model": response_model,
        "choices": choices,
        "usage": usage,
        "chunk_count": chunk_count,
        "first_visible_seconds": first_content_seconds,
        "total_seconds": total_seconds,
    }


def print_parsed_response(label: str, result: dict) -> None:
    print(f"\n=== {label} 完整解析 ===")
    print(f"id={result['id']}")
    print(f"model={result['model']}")
    if "chunk_count" in result:
        print(f"chunk_count={result['chunk_count']}")
    for choice in result["choices"]:
        print(f"choice[{choice['index']}].finish_reason={choice['finish_reason']}")
        print(f"choice[{choice['index']}].content={choice['content']}")
    print(f"usage={result['usage']}")


def main() -> None:
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
    non_streaming = run_non_streaming(client)
    streaming = run_streaming(client)

    print_parsed_response("非流式", non_streaming)
    print_parsed_response("流式", streaming)

    streaming_first = streaming["first_visible_seconds"]
    streaming_first_text = (
        f"{streaming_first:.3f}s" if streaming_first is not None else "未收到内容 chunk"
    )
    print("\n=== 时延对比（客户端观测值） ===")
    print(
        "非流式: "
        f"首个可见内容={non_streaming['first_visible_seconds']:.3f}s, "
        f"总耗时={non_streaming['total_seconds']:.3f}s"
    )
    print(
        "流式:   "
        f"首个内容 chunk={streaming_first_text}, "
        f"总耗时={streaming['total_seconds']:.3f}s"
    )


if __name__ == "__main__":
    main()
