#!/usr/bin/env python3
"""Compare Hy3 non-streaming total latency with streaming first-token latency.

Environment:
  HY3_BASE_URL=http://127.0.0.1:8000/v1
  HY3_API_KEY=EMPTY
  HY3_MODEL=hy3

Run:
  python3 examples/api/latency_compare.py

Sample output:
  non_streaming_total_s: 2.314
  streaming_first_token_s: 0.482
  streaming_total_s: 2.102
"""

from __future__ import annotations

import time

from common import MODEL, make_client, print_json, print_runtime_config, request_options


def main() -> None:
    print_runtime_config()
    client = make_client()
    messages = [
        {
            "role": "user",
            "content": "Write a concise checklist for productionizing a Hy3 API client.",
        }
    ]

    base_request = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.7,
        "top_p": 1.0,
        "max_tokens": 256,
        **request_options(reasoning_effort="no_think"),
    }

    print_json("non_streaming request", base_request)
    non_streaming_start = time.perf_counter()
    non_streaming_response = client.chat.completions.create(**base_request)
    non_streaming_total = time.perf_counter() - non_streaming_start
    non_streaming_text = non_streaming_response.choices[0].message.content or ""

    print("\n=== non_streaming parsed response ===")
    print("finish_reason:", non_streaming_response.choices[0].finish_reason)
    print("content:", non_streaming_text)
    print("non_streaming_total_s:", round(non_streaming_total, 3))
    if non_streaming_response.usage:
        print_json("non_streaming usage", non_streaming_response.usage)

    streaming_request = dict(base_request)
    streaming_request["stream"] = True

    print_json("streaming request", streaming_request)
    streaming_start = time.perf_counter()
    stream = client.chat.completions.create(**streaming_request)

    first_token_latency = None
    chunk_count = 0
    content_parts: list[str] = []

    for chunk in stream:
        chunk_count += 1
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        content = getattr(delta, "content", None)
        reasoning_content = getattr(delta, "reasoning_content", None)
        if content:
            content_parts.append(content)
        if first_token_latency is None and (content or reasoning_content):
            first_token_latency = time.perf_counter() - streaming_start

    streaming_total = time.perf_counter() - streaming_start
    streaming_text = "".join(content_parts)

    print("\n=== latency comparison ===")
    print("chunk_count:", chunk_count)
    print("streaming_first_token_s:", round(first_token_latency or 0.0, 3))
    print("streaming_total_s:", round(streaming_total, 3))
    print("non_streaming_total_s:", round(non_streaming_total, 3))
    print("streaming_content:", streaming_text)


if __name__ == "__main__":
    main()
