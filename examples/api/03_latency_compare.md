# Non-streaming vs Streaming Latency

This example compares non-streaming and streaming Hy3 API requests.

It measures:

* non-streaming total latency
* client-observed Time To First Token (TTFT)
* streaming total latency
* number of received streaming chunks
* streaming finish reason

The main goal is to demonstrate the difference between **total completion time** and **perceived responsiveness**.

## Prerequisites

Before running this example, make sure you have:

* Python 3.10 or later
* the `openai` Python package installed
* access to a Hy3 OpenAI-compatible endpoint

The example reads:

```text
HY3_BASE_URL
HY3_API_KEY
HY3_MODEL
```

If these variables are not set, it uses:

```text
HY3_BASE_URL=http://127.0.0.1:8000/v1
HY3_API_KEY=EMPTY
HY3_MODEL=hy3
```

## Run the example

From the repository root:

```bash
python examples/api/03_latency_compare.py
```

The script sends two requests with the same prompt and generation parameters:

1. a non-streaming request
2. a streaming request

This helps make the comparison easier to interpret.

## Non-streaming request

The non-streaming request sets:

```python
"stream": False
```

Complete request:

```python
request_payload = {
    "model": model,
    "messages": [
        {
            "role": "user",
            "content": (
                "Explain the difference between "
                "Redis and MySQL in about 150 words."
            ),
        }
    ],
    "temperature": 0.9,
    "top_p": 1.0,
    "stream": False,
    "extra_body": {
        "chat_template_kwargs": {
            "reasoning_effort": "no_think"
        }
    },
}
```

Total latency is measured with `time.perf_counter()`:

```python
start_time = time.perf_counter()

response = client.chat.completions.create(
    **request_payload
)

end_time = time.perf_counter()

total_latency = end_time - start_time
```

In non-streaming mode, the client waits for the complete response before it can access the final assistant message.

## Streaming request

The streaming request uses the same prompt and generation parameters, but sets:

```python
"stream": True
```

Complete request:

```python
request_payload = {
    "model": model,
    "messages": [
        {
            "role": "user",
            "content": (
                "Explain the difference between "
                "Redis and MySQL in about 150 words."
            ),
        }
    ],
    "temperature": 0.9,
    "top_p": 1.0,
    "stream": True,
    "extra_body": {
        "chat_template_kwargs": {
            "reasoning_effort": "no_think"
        }
    },
}
```

The stream is consumed incrementally:

```python
stream = client.chat.completions.create(
    **request_payload
)

for chunk in stream:
    ...
```

## Measuring TTFT

The example records the request start time:

```python
start_time = time.perf_counter()
```

It then waits for the first chunk containing text content:

```python
if delta.content is not None:
    if first_token_time is None:
        first_token_time = time.perf_counter()
```

TTFT is calculated as:

```python
ttft = first_token_time - start_time
```

In this example, TTFT should be interpreted as:

> the elapsed time from starting the API request until the client first observes a non-`None` text delta

This is a client-observed measurement. It includes more than model generation alone and may also reflect server processing, network transfer, and client-side stream parsing.

## Measuring streaming total latency

The end time is recorded after the stream finishes:

```python
end_time = time.perf_counter()

total_latency = end_time - start_time
```

The example also counts all received chunks:

```python
chunk_count += 1
```

and records the finish reason:

```python
if choice.finish_reason is not None:
    finish_reason = choice.finish_reason
```

## Response parsing

For the non-streaming response, the complete response object is printed:

```python
print(response.model_dump_json(indent=2))
```

The assistant content is parsed from:

```python
response.choices[0].message.content
```

For the streaming response, each text fragment is read from:

```python
chunk.choices[0].delta.content
```

The fragments are preserved:

```python
text_parts.append(delta.content)
```

and reconstructed after streaming completes:

```python
full_content = "".join(text_parts)
```

## Example output

The following output was observed during an example Hy3 API run:

```text
=== Latency comparison ===

Non-streaming:
Total latency: 5.706s

Streaming:
TTFT: 1.367s
Total latency: 5.365s
Chunks received: 96
Finish reason: stop

Note:
Streaming can improve perceived responsiveness by delivering content before the full response is complete. It does not guarantee lower total latency.
```

Exact measurements will vary between runs.

Latency can be affected by factors such as:

* endpoint load
* network conditions
* serving infrastructure
* prompt length
* generated output length
* sampling behavior
* model configuration

## Interpreting the results

In the example run:

```text
Non-streaming total latency: 5.706s
Streaming TTFT:             1.367s
Streaming total latency:    5.365s
```

The streaming request began delivering visible text substantially earlier than the non-streaming request returned its complete response.

However, this does not prove that streaming always has lower total latency.

The main benefit of streaming is often improved perceived responsiveness:

```text
Non-streaming:
request -> wait -> wait -> wait -> complete response

Streaming:
request -> first text -> more text -> more text -> complete response
```

## Important limitations

This script is intended as a practical developer example, not a rigorous benchmark.

The two requests are executed separately, so conditions may differ between them. In addition, `temperature=0.9` allows sampling variation, which means generated outputs may differ in length and content.

For rigorous benchmarking, consider:

* multiple repeated runs
* warm-up requests
* fixed or lower-variance generation settings
* output length normalization
* percentile metrics such as p50 and p95
* controlled network and server conditions

## What this example demonstrates

This example shows:

1. how to measure non-streaming total latency
2. how to measure client-observed streaming TTFT
3. how to measure streaming total latency
4. how to count received chunks
5. why streaming can improve perceived responsiveness
6. why streaming does not guarantee lower total completion time
