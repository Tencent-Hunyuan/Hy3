"""Compare Chat Completions streaming and non-streaming latency."""

import os
import time

from openai import OpenAI


def create_client() -> OpenAI:
    return OpenAI(
        api_key=os.environ["HY3_API_KEY"],
        base_url=os.getenv(
            "HY3_BASE_URL",
            "https://tokenhub.tencentmaas.com/v1",
        ),
    )


def main():
    client = create_client()
    messages = [{"role": "user", "content": "请用三句话介绍深圳。"}]

    # Measure the complete non-streaming response time.
    start = time.perf_counter()
    response = client.chat.completions.create(
        model="hy3",
        messages=messages,
        stream=False,
    )
    non_streaming_total = time.perf_counter() - start

    # Measure both first-chunk latency and total streaming time.
    start = time.perf_counter()
    first_chunk_time = None
    chunks = []
    for chunk in client.chat.completions.create(
        model="hy3",
        messages=messages,
        stream=True,
    ):
        if first_chunk_time is None:
            first_chunk_time = time.perf_counter() - start
        if chunk.choices and chunk.choices[0].delta.content:
            chunks.append(chunk.choices[0].delta.content)
    streaming_total = time.perf_counter() - start

    print(f"non-streaming total: {non_streaming_total:.3f}s")
    print(f"streaming first chunk: {first_chunk_time:.3f}s")
    print(f"streaming total: {streaming_total:.3f}s")
    print(f"streaming text: {''.join(chunks)}")
    print(f"non-streaming text: {response.choices[0].message.content}")


if __name__ == "__main__":
    main()
