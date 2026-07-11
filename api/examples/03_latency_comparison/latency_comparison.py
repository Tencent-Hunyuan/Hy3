"""Compare first-token latency and total latency."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import create_client, model_name  # noqa: E402


def main() -> None:
    client = create_client()
    request = {
        "model": model_name(),
        "messages": [{"role": "user", "content": "解释什么是二分查找。"}],
        "max_tokens": 512,
        "extra_body": {"chat_template_kwargs": {"reasoning_effort": "no_think"}},
    }

    started = time.perf_counter()
    response = client.chat.completions.create(**request)
    non_streaming_total = time.perf_counter() - started

    started = time.perf_counter()
    first_token = None
    parts: list[str] = []
    finish_reason = None
    streaming_usage = None
    stream = client.chat.completions.create(
        **request, stream=True, stream_options={"include_usage": True}
    )
    for chunk in stream:
        if chunk.usage:
            streaming_usage = chunk.usage
        if not chunk.choices:
            continue
        choice = chunk.choices[0]
        if choice.delta.content:
            if first_token is None:
                first_token = time.perf_counter() - started
            parts.append(choice.delta.content)
        finish_reason = choice.finish_reason or finish_reason
    streaming_total = time.perf_counter() - started

    print("=== Non-streaming ===")
    print("id:", response.id)
    print("model:", response.model)
    print("content:", response.choices[0].message.content)
    print("finish_reason:", response.choices[0].finish_reason)
    if response.usage:
        print(
            "usage:",
            f"prompt={response.usage.prompt_tokens}, "
            f"completion={response.usage.completion_tokens}, "
            f"total={response.usage.total_tokens}",
        )
    print(f"total latency: {non_streaming_total:.3f}s")
    print("\n=== Streaming ===")
    print("content:", "".join(parts))
    print(
        f"first token latency: {first_token:.3f}s"
        if first_token
        else "no content token"
    )
    print(f"total latency: {streaming_total:.3f}s")
    print("finish_reason:", finish_reason)
    if streaming_usage:
        print(
            "usage:",
            f"prompt={streaming_usage.prompt_tokens}, "
            f"completion={streaming_usage.completion_tokens}, "
            f"total={streaming_usage.total_tokens}",
        )


if __name__ == "__main__":
    main()
