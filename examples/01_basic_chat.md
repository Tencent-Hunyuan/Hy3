# 01 Basic Chat

This example shows the two most common chat patterns:

- Single-turn chat: one user message and one assistant answer.
- Multi-turn chat: append previous assistant answers to `messages` before asking follow-up questions.

Script: [01_basic_chat.py](01_basic_chat.py)

## Complete Request

The single-turn request uses the OpenAI-compatible Chat Completions API:

```python
response = client.chat.completions.create(
    model=MODEL,
    messages=[
        {
            "role": "user",
            "content": "Give me three practical tips for writing reliable API clients.",
        },
    ],
    temperature=0.9,
    top_p=1.0,
    max_tokens=512,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)
```

The multi-turn request keeps a shared `messages` list:

```python
messages = [
    {"role": "system", "content": "You are a concise developer assistant."},
    {"role": "user", "content": "Explain what an API timeout is in one sentence."},
]

first = client.chat.completions.create(model=MODEL, messages=messages)
answer = first.choices[0].message.content
messages.append({"role": "assistant", "content": answer})
messages.append({"role": "user", "content": "Now give me one Python mitigation."})

second = client.chat.completions.create(model=MODEL, messages=messages)
```

## Complete Response Parsing

Non-streaming chat returns the full assistant message in one response:

```text
response
└── choices[0]
    └── message
        └── content = assistant answer
```

The script reads it with:

```python
print(response.choices[0].message.content)
```

For multi-turn chat, the first answer is also appended back into `messages` as an assistant message so the second request has conversation history.

## Run

```bash
python examples/01_basic_chat.py
```

## Example Output

```text
=== Single Turn ===
1. Set explicit timeouts for every request.
2. Retry only transient failures with exponential backoff.
3. Log request IDs and clear error messages for debugging.

=== Multi Turn ===
Assistant: An API timeout is the maximum time a client waits for a server response before treating the request as failed.
Assistant: In Python, pass a timeout value when creating the client or when sending the request.
```
