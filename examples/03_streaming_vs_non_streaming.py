import os
import time

from openai import OpenAI

BASE_URL = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.getenv("HY3_API_KEY", "EMPTY")
MODEL = os.getenv("HY3_MODEL", "hy3")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)


def main() -> None:
    messages = [{"role": "user", "content": "Explain API retries in about 120 words."}]

    start = time.perf_counter()
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=256,
    )
    non_stream_text = response.choices[0].message.content or ""
    non_stream_total = time.perf_counter() - start

    start = time.perf_counter()
    first_token_time = None
    text_chunks = []

    stream = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=256,
        stream=True,
    )

    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta and delta.content:
            if first_token_time is None:
                first_token_time = time.perf_counter() - start
            text_chunks.append(delta.content)

    stream_text = "".join(text_chunks)
    stream_total = time.perf_counter() - start

    print(f"Non-streaming total: {non_stream_total:.3f}s")
    first_token = f"{first_token_time:.3f}s" if first_token_time is not None else "n/a"
    print(f"Streaming first token: {first_token}")
    print(f"Streaming total: {stream_total:.3f}s")
    print(f"Non-streaming answer length: {len(non_stream_text)} chars")
    print(f"Streaming answer length: {len(stream_text)} chars")


if __name__ == "__main__":
    main()
