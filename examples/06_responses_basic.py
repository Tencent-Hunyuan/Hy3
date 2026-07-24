"""Run a minimal Responses API request."""

import os

from openai import OpenAI


def main():
    # Create an OpenAI-compatible client for the Responses endpoint.
    client = OpenAI(
        api_key=os.environ["HY3_API_KEY"],
        base_url=os.getenv(
            "HY3_BASE_URL",
            "https://tokenhub.tencentmaas.com/v1",
        ),
    )

    # Responses API uses top-level instructions and input fields.
    response = client.responses.create(
        model="hy3",
        instructions="你是一个有帮助的助手。",
        input="你好，请简单介绍一下腾讯混元大模型。",
        stream=False,
    )

    # output_text is the convenient field for the final text answer.
    print(response.output_text)


if __name__ == "__main__":
    main()
