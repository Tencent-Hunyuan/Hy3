# Basic Chat

This example demonstrates how to call the Hy3 OpenAI-compatible API for:

* single-turn chat
* multi-turn chat
* complete request inspection
* response parsing
* token usage inspection

## Prerequisites

Before running this example, make sure you have:

* Python 3.10 or later
* the `openai` Python package installed
* access to a Hy3 OpenAI-compatible endpoint

The example reads the following environment variables:

```text
HY3_BASE_URL
HY3_API_KEY
HY3_MODEL
```

If they are not set, the example uses these defaults:

```text
HY3_BASE_URL=http://127.0.0.1:8000/v1
HY3_API_KEY=EMPTY
HY3_MODEL=hy3
```

For a self-hosted Hy3 deployment, make sure the local API server is running before executing the example.

## Run the example

From the repository root:

```bash
python examples/api/01_basic_chat.py
```

## Single-turn chat

The single-turn example sends one user message to Hy3.

### Complete request

```python
request_payload = {
    "model": model,
    "messages": [
        {
            "role": "user",
            "content": "Hello! Can you briefly introduce yourself?",
        }
    ],
    "temperature": 0.9,
    "top_p": 1.0,
    "extra_body": {
        "chat_template_kwargs": {
            "reasoning_effort": "no_think"
        }
    },
}

response = client.chat.completions.create(
    **request_payload
)
```

The request payload is printed before it is sent:

```python
print_request(request_payload)
```

This makes it easier to inspect the exact model, messages, sampling parameters, and reasoning configuration used by the request.

## Response parsing

The OpenAI Python SDK returns a structured response object.

The example first prints the complete response:

```python
print(response.model_dump_json(indent=2))
```

It then parses several commonly used fields:

```python
choice = response.choices[0]

print(f"Response ID: {response.id}")
print(f"Model: {response.model}")
print(f"Finish reason: {choice.finish_reason}")
print(f"Role: {choice.message.role}")
print(f"Content: {choice.message.content}")
```

When usage information is available, the example also prints token counts:

```python
if response.usage is not None:
    print(f"Prompt tokens: {response.usage.prompt_tokens}")
    print(f"Completion tokens: {response.usage.completion_tokens}")
    print(f"Total tokens: {response.usage.total_tokens}")
```

## Multi-turn chat

The multi-turn example demonstrates how conversation history is preserved by the client.

The first request contains:

```python
messages = [
    {
        "role": "user",
        "content": "My name is Ben. Please remember it.",
    }
]
```

After receiving the assistant response, the example appends it to the message history:

```python
messages.append(
    {
        "role": "assistant",
        "content": first_reply,
    }
)
```

Then it appends the next user message:

```python
messages.append(
    {
        "role": "user",
        "content": "What is my name?",
    }
)
```

The second request therefore includes the complete conversation history.

Conceptually, the request history looks like this:

```json
[
  {
    "role": "user",
    "content": "My name is Ben. Please remember it."
  },
  {
    "role": "assistant",
    "content": "Got it, Ben. I'll remember your name."
  },
  {
    "role": "user",
    "content": "What is my name?"
  }
]
```

Hy3 can answer the second question because the previous conversation turns are included again in the request.

The API itself does not automatically preserve conversation state between independent requests. Applications should maintain and resend the relevant message history when implementing multi-turn chat.

## Example output

The exact generated text may vary between runs.

Example:

```text
=== Single-turn chat ===

--- Parsed response ---
Response ID: 7f2b3c5a-example
Model: hy3
Finish reason: stop
Role: assistant
Content: Hello! I'm Hunyuan, a large model developed by Tencent...

--- Token usage ---
Prompt tokens: 18
Completion tokens: 31
Total tokens: 49


=== Multi-turn chat ===

### First turn

--- Parsed response ---
Model: hy3
Finish reason: stop
Role: assistant
Content: Got it, Ben — I'll remember your name.

### Second turn

--- Parsed response ---
Model: hy3
Finish reason: stop
Role: assistant
Content: Your name is Ben.

--- Token usage ---
Prompt tokens: 56
Completion tokens: 6
Total tokens: 62
```

Response IDs, generated text, latency, and token usage may vary depending on the request, endpoint, model serving configuration, and generation behavior.

## What this example demonstrates

This example shows four core concepts:

1. How to construct a Hy3 chat completion request.
2. How to inspect the complete request payload.
3. How to parse structured response fields and token usage.
4. How to implement multi-turn conversation by preserving message history.
