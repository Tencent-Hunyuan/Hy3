#!/usr/bin/env python3
"""Hy3 streaming example: request with stream=True and parse every chunk.

Environment:
  HY3_BASE_URL=http://127.0.0.1:8000/v1
  HY3_API_KEY=EMPTY
  HY3_MODEL=hy3

Run:
  python3 examples/api/streaming.py

Sample output:
  chunk=000 role=assistant content='' finish_reason=None
  chunk=001 role=None content='Hy3' finish_reason=None
  ...
  final_content: Hy3 can help with API integration...
"""

from __future__ import annotations

from typing import Any

from common import (
    MODEL,
    make_client,
    print_json,
    print_runtime_config,
    request_options,
    to_plain,
)


def main() -> None:
    print_runtime_config()
    client = make_client()

    request = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": "List four steps for validating a Hy3 API integration.",
            }
        ],
        "temperature": 0.7,
        "top_p": 1.0,
        "max_tokens": 256,
        "stream": True,
        **request_options(reasoning_effort="no_think"),
    }

    print_json("streaming request", request)

    stream = client.chat.completions.create(**request)
    content_parts: list[str] = []
    reasoning_parts: list[str] = []
    tool_call_deltas: list[Any] = []

    print("\n=== streaming chunks ===")
    for index, chunk in enumerate(stream):
        if not chunk.choices:
            print(f"chunk={index:03d} choices=[]")
            continue

        choice = chunk.choices[0]
        delta = choice.delta
        role = getattr(delta, "role", None)
        content = getattr(delta, "content", None)
        reasoning_content = getattr(delta, "reasoning_content", None) or getattr(
            delta, "reasoning", None
        )
        reasoning_details = getattr(delta, "reasoning_details", None)
        tool_calls = getattr(delta, "tool_calls", None)

        if content:
            content_parts.append(content)
        if reasoning_content:
            reasoning_parts.append(reasoning_content)
        if reasoning_details:
            reasoning_parts.append(str(to_plain(reasoning_details)))
        if tool_calls:
            tool_call_deltas.extend(tool_calls)

        print(
            "chunk={idx:03d} id={id} role={role!r} content={content!r} "
            "reasoning_delta={reasoning!r} reasoning_details={reasoning_details} tool_calls={tool_calls} "
            "finish_reason={finish!r}".format(
                idx=index,
                id=chunk.id,
                role=role,
                content=content,
                reasoning=reasoning_content,
                reasoning_details=json.dumps(to_plain(reasoning_details), ensure_ascii=False)
                if reasoning_details
                else None,
                tool_calls=json.dumps(to_plain(tool_calls), ensure_ascii=False)
                if tool_calls
                else None,
                finish=choice.finish_reason,
            )
        )

    print("\n=== final assembled response ===")
    print("final_content:", "".join(content_parts))
    if reasoning_parts:
        print("final_reasoning_content:", "".join(reasoning_parts))
    if tool_call_deltas:
        print_json("tool_call_deltas", tool_call_deltas)


if __name__ == "__main__":
    main()
