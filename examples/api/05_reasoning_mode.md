# Reasoning Mode

This example compares Hy3 reasoning behavior with:

* `no_think`
* `high`

It demonstrates how reasoning mode can affect:

* response latency
* reasoning token usage
* completion token usage
* returned reasoning metadata
* final answer behavior

> This example is a practical demonstration, not a benchmark. Results may vary between runs and serving environments.

## Prerequisites

Before running this example, make sure you have:

* Python 3.10 or later
* the `openai` Python package installed
* access to a Hy3 OpenAI-compatible endpoint
* an endpoint that supports Hy3 reasoning mode configuration

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
python examples/api/05_reasoning_mode.py
```

The script sends the same reasoning problem twice:

1. once with `no_think`
2. once with `high`

## Test prompt

The example uses the following prompt:

```text
A company has 100 employees.
60 know Python, 45 know Java, and 30 know SQL.
25 know both Python and Java,
20 know both Python and SQL,
15 know both Java and SQL,
and 10 know all three languages.

How many employees know none of the three languages?
Give the final answer and a concise explanation.
```

The correct solution uses inclusion–exclusion:

```text
60 + 45 + 30
- 25 - 20 - 15
+ 10
= 85
```

Therefore:

```text
100 - 85 = 15
```

The correct answer is:

```text
15 employees
```

## Complete request

The request payload is constructed as follows:

```python
request_payload = {
    "model": model,
    "messages": [
        {
            "role": "user",
            "content": PROMPT,
        }
    ],
    "temperature": 0.9,
    "top_p": 1.0,
    "extra_body": {
        "reasoning_effort": reasoning_effort
    },
}
```

The value of `reasoning_effort` is changed between runs.

For direct-answer mode:

```python
run_reasoning_mode("no_think")
```

For higher reasoning effort:

```python
run_reasoning_mode("high")
```

## Important endpoint compatibility note

Reasoning configuration may depend on the serving environment.

This example sends:

```json
{
  "reasoning_effort": "high"
}
```

as a top-level request-body field through `extra_body`.

Some self-hosted Hy3 serving configurations may instead expose reasoning options through serving-specific chat-template parameters.

Always check the documentation for the endpoint or serving stack you are using.

## Measuring latency

Each request is timed with:

```python
start_time = time.perf_counter()

response = client.chat.completions.create(
    **request_payload
)

end_time = time.perf_counter()

latency = end_time - start_time
```

The reported latency is client-observed end-to-end latency.

It may include:

* server-side processing
* model generation
* network transfer
* response decoding

## Parsing the final answer

The final assistant message is read from:

```python
message = response.choices[0].message
```

and the final answer from:

```python
message.content
```

The finish reason is available through:

```python
response.choices[0].finish_reason
```

## Parsing reasoning content

Some compatible endpoints may return a `reasoning_content` field.

The example accesses the serialized message data:

```python
message_data = (
    response
    .choices[0]
    .message
    .model_dump()
)
```

Then reads:

```python
reasoning_content = message_data.get(
    "reasoning_content"
)
```

Because this field is endpoint-dependent, the example treats it as optional:

```python
if isinstance(reasoning_content, str):
    return reasoning_content

return None
```

The comparison reports whether reasoning content was returned and, when present, its length.

## Parsing reasoning token usage

When available, reasoning token usage is read from:

```python
response.usage.completion_tokens_details
```

and:

```python
details.reasoning_tokens
```

The example safely handles cases where usage details are absent.

## Example output

The following result was observed during one Hy3 API run:

```text
=== Reasoning mode comparison ===

no_think:
Latency: 5.098s
Reasoning tokens: 0
Completion tokens: 91
Total tokens: 180
Reasoning content returned: no
Final answer: 20 employees

high:
Latency: 9.894s
Reasoning tokens: 548
Completion tokens: 637
Total tokens: 723
Reasoning content returned: yes
Reasoning content length: 1763
Final answer: 15 employees
```

In this specific run:

* `no_think` used no reported reasoning tokens
* `high` used 548 reported reasoning tokens
* `high` returned reasoning content
* `high` had higher latency
* `high` used substantially more completion tokens
* the `no_think` response contained an arithmetic error
* the `high` response produced the correct final answer

The `no_think` response correctly calculated that 85 employees knew at least one language, but then incorrectly evaluated:

```text
100 - 85 = 20
```

The correct subtraction is:

```text
100 - 85 = 15
```

The `high` response produced the correct result:

```text
15 employees
```

## Interpreting the result

This single run illustrates a possible trade-off:

```text
no_think
→ lower observed latency
→ fewer tokens
→ no returned reasoning content
→ incorrect final answer in this run

high
→ higher observed latency
→ more tokens
→ reasoning content returned
→ correct final answer in this run
```

However, this should not be interpreted as proof that `high` is always more accurate or that `no_think` is always faster.

A single request pair is not a benchmark.

Results can vary because of:

* model sampling
* endpoint load
* prompt characteristics
* serving configuration
* network conditions
* model updates

## Reasoning content and application design

Applications should not assume that every endpoint or reasoning mode returns reasoning content.

Code should treat fields such as:

```text
reasoning_content
reasoning_tokens
```

as optional unless the endpoint contract guarantees them.

Applications should also avoid depending on hidden or intermediate reasoning text for correctness. The final answer and externally verifiable results should remain the primary basis for application behavior.

## What this example demonstrates

This example shows:

1. how to switch between `no_think` and `high`
2. how to send reasoning configuration
3. how to measure client-observed latency
4. how to inspect reasoning token usage
5. how to detect optional reasoning content
6. how reasoning modes may differ in cost and latency
7. why a single comparison should not be treated as a benchmark
8. why final answers should still be independently validated
