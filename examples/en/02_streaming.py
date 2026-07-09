"""
Hy3 Streaming Output Example (examples/02_streaming.py)

Demonstrates how to call Hy3 in streaming mode via the OpenAI-compatible API,
receiving incremental output token by token and finally assembling the full text.

Before running, deploy the Hy3 service via vLLM / SGLang (listens on 127.0.0.1:8000 by default).
Connection info can be overridden via environment variables:
    HY3_BASE_URL  service address (default http://127.0.0.1:8000/v1)
    HY3_API_KEY   API key (any value works for local deployment, default EMPTY)
"""

import os

from openai import OpenAI

client = OpenAI(
    base_url=os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
    api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
)

# A prompt that elicits a multi-sentence answer
messages = [
    {
        "role": "user",
        "content": (
            "请用中文写一段关于「秋天的银杏林」的短文，"
            "包含颜色、声音和心情的描写，至少三句话。"
        ),
    },
]

print("=== Streaming Output (per-chunk print) ===")
stream = client.chat.completions.create(
    model="hy3",
    messages=messages,
    temperature=0.9,
    top_p=1.0,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
    stream=True,
)

full_text_parts = []
for chunk in stream:
    # Each chunk in the stream is a ChatCompletionChunk
    if not chunk.choices:
        continue
    delta = chunk.choices[0].delta
    content = delta.content
    if content:  # skip None / empty string
        # Print incremental content in real time (no newline, typewriter effect)
        print(content, end="", flush=True)
        full_text_parts.append(content)

print("\n\n=== Stream ended, assembling full text ===")
full_text = "".join(full_text_parts)
print(full_text)
