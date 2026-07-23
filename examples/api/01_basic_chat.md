# 01 — Basic chat and conversation state

Use this example to verify configuration, inspect a complete response, and see
how chat history is carried into the next request.

## Run

```bash
python examples/api/01_basic_chat.py
```

The script makes one single-turn request, followed by two calls that form a
multi-turn conversation. That means one execution consumes three API requests.

## Complete request

The script builds the request explicitly before sending it:

```python
request = {
    "model": config.model,
    "messages": [
        {
            "role": "user",
            "content": "Give three practical uses for a 256K context window.",
        }
    ],
    "temperature": 0.9,
    "top_p": 1.0,
    "max_tokens": 512,
    "extra_body": {
        "chat_template_kwargs": {"reasoning_effort": "no_think"}
    },
}
response = client.chat.completions.create(**request)
```

For the second turn, append both the first assistant answer and the new user
question. Sending only the newest question would discard conversation state:

```python
history.extend(
    [
        {"role": "assistant", "content": first_reply},
        {"role": "user", "content": "Now name one trade-off, in the same context."},
    ]
)
response = client.chat.completions.create(model=config.model, messages=history, ...)
```

## Complete response parsing

```python
choice = response.choices[0]
message = choice.message

print(message.content)              # final user-facing answer
print(choice.finish_reason)         # normally "stop"; "length" means truncation
if response.usage:
    print(response.usage.prompt_tokens)
    print(response.usage.completion_tokens)
    print(response.usage.total_tokens)
```

The runnable script also detects separately returned `reasoning_content` without
printing it by default.

## Example output

The text below illustrates the output format; generated wording and token counts
will differ. Replace it with a dated, redacted live capture before claiming a
specific endpoint was tested.

```text
=== Single turn ===
Assistant: A long context window can support repository analysis, document synthesis, and long conversations.
Finish reason: stop
Tokens: prompt=<count>, completion=<count>, total=<count>

=== Multi turn ===
Assistant: Streaming lets a user see output before the full response is ready.
Finish reason: stop
Assistant: It requires incremental parsing and more careful error handling.
Finish reason: stop
```

## Checks

- Confirm the printed request contains no API key.
- Treat `finish_reason="length"` as a signal to raise `max_tokens` or shorten the prompt.
- Preserve roles and ordering when adding messages to history.
