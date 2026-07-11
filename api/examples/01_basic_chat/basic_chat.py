"""Single-turn and multi-turn Hy3 chat calls."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import create_client, model_name, print_response  # noqa: E402


def main() -> None:
    client = create_client()
    model = model_name()

    print("=== Single turn ===")
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "用一句话介绍 Hy3。"}],
        temperature=0.9,
        top_p=1.0,
        max_tokens=256,
        extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
    )
    print_response(response)

    print("\n=== Multi turn ===")
    messages = [
        {"role": "system", "content": "你是一个简洁、准确的技术助手。"},
        {"role": "user", "content": "Python 中的列表推导式是什么？"},
    ]
    first = client.chat.completions.create(model=model, messages=messages)
    messages.append(first.choices[0].message.model_dump(exclude_none=True))
    messages.append({"role": "user", "content": "给一个只保留偶数的例子。"})
    second = client.chat.completions.create(model=model, messages=messages)
    print_response(second)


if __name__ == "__main__":
    main()
