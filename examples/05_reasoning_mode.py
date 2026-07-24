"""Compare normal and reasoning modes for Chat Completions."""

import os

from openai import OpenAI


def main():
    client = OpenAI(
        api_key=os.environ["HY3_API_KEY"],
        base_url=os.getenv(
            "HY3_BASE_URL",
            "https://tokenhub.tencentmaas.com/v1",
        ),
    )
    messages = [{"role": "user", "content": "请计算 37 × 24，并简要说明结果。"}]

    # Compare a normal request with a reasoning-enabled request.
    normal = client.chat.completions.create(
        model="hy3",
        messages=messages,
    )
    reasoning = client.chat.completions.create(
        model="hy3",
        messages=messages,
        reasoning_effort="high",
    )

    print("Normal mode:")
    print(normal.choices[0].message.content)
    print("\nReasoning mode:")
    print(reasoning.choices[0].message.content)
    print("\nReasoning usage:")
    print(reasoning.usage)


if __name__ == "__main__":
    main()
