"""Parse a Hy3 streaming response chunk by chunk."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import create_client, model_name  # noqa: E402


def main() -> None:
    stream = create_client().chat.completions.create(
        model=model_name(),
        messages=[{"role": "user", "content": "列出三个学习 Python 的建议。"}],
        stream=True,
        stream_options={"include_usage": True},
        extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
    )

    content_parts: list[str] = []
    reasoning_parts: list[str] = []
    finish_reason = None
    usage = None
    for chunk in stream:
        print(f"chunk id={chunk.id}")
        if chunk.usage:
            usage = chunk.usage
        if not chunk.choices:
            continue
        choice = chunk.choices[0]
        delta = choice.delta
        reasoning = getattr(delta, "reasoning_content", None)
        if reasoning:
            reasoning_parts.append(reasoning)
            print(f"  reasoning={reasoning!r}")
        if delta.content:
            content_parts.append(delta.content)
            print(f"  content={delta.content!r}")
        if choice.finish_reason:
            finish_reason = choice.finish_reason

    print("\n=== Parsed response ===")
    if reasoning_parts:
        print("reasoning_content:", "".join(reasoning_parts))
    print("content:", "".join(content_parts))
    print("finish_reason:", finish_reason)
    if usage:
        print(
            "usage:",
            f"prompt={usage.prompt_tokens}, completion={usage.completion_tokens}, "
            f"total={usage.total_tokens}",
        )


if __name__ == "__main__":
    main()
