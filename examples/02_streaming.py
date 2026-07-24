"""Stream a Chat Completions response and print usage."""

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

    # Request an SSE stream and ask for usage in the final chunk.
    stream = client.chat.completions.create(
        model="hy3",
        messages=[{"role": "user", "content": "请用三句话介绍深圳。"}],
        stream=True,
        stream_options={"include_usage": True},
    )

    # Concatenate text deltas as chunks arrive.
    for chunk in stream:
        if chunk.choices:
            delta = chunk.choices[0].delta
            if delta.content:
                print(delta.content, end="", flush=True)

        # With include_usage enabled, the last chunk may have no choices
        # but can still contain complete usage statistics.
        if chunk.usage:
            print(f"\n\nusage: {chunk.usage}")


if __name__ == "__main__":
    main()
