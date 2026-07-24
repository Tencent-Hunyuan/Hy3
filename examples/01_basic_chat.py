"""Run a minimal Hy3 Chat Completions request with the OpenAI SDK."""

import os

from openai import OpenAI


def main():
    # Create an OpenAI-compatible client for TokenHub.
    client = OpenAI(
        api_key=os.environ["HY3_API_KEY"],
        base_url=os.getenv(
            "HY3_BASE_URL",
            "https://tokenhub.tencentmaas.com/v1",
        ),
    )

    # Send a non-streaming Chat Completions request.
    response = client.chat.completions.create(
        model="hy3",
        messages=[
            {"role": "system", "content": "你是一个有帮助的助手。"},
            {"role": "user", "content": "你好，请简单介绍一下你自己。"},
        ],
        stream=False,
    )

    # Read the assistant text from the first choice.
    print(response.choices[0].message.content)


if __name__ == "__main__":
    main()
