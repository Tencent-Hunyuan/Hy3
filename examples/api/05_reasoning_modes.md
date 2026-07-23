# 05 — Comparing reasoning modes

Hy3 accepts `no_think`, `low`, and `high` through its chat-template options.
This example submits one availability problem in all three modes and reports
latency plus the amount of separately returned reasoning text.

## Run

```bash
python examples/api/05_reasoning_modes.py
```

Reasoning text is hidden by default. To inspect it in a private development
terminal:

```bash
HY3_SHOW_REASONING=1 python examples/api/05_reasoning_modes.py
```

Do not place private reasoning, secrets, or user data in logs.

## Complete request

The request body is identical except for effort and output budget:

```python
prompt = (
    "A service has 99.9% availability. Assuming independent downtime, what is the "
    "probability that two redundant instances are both unavailable? Explain briefly."
)

response = client.chat.completions.create(
    model=config.model,
    messages=[{"role": "user", "content": prompt}],
    temperature=0.0,
    top_p=1.0,
    max_tokens=2048 if effort == "high" else 768,
    extra_body={
        "chat_template_kwargs": {"reasoning_effort": effort}
    },
)
```

## Complete response parsing

Some OpenAI-compatible SDK models preserve extension fields in `model_extra`.
The example's helper supports both normal attributes and that fallback:

```python
message = response.choices[0].message
reasoning = getattr(message, "reasoning_content", None)
if reasoning is None and message.model_extra:
    reasoning = message.model_extra.get("reasoning_content")

final_answer = message.content or ""
print("Reasoning characters returned:", len(reasoning or ""))
print("Final answer:", final_answer)
```

Use `content`, not `reasoning_content`, as the normal user-facing result.

## Example output

Illustrative format only; latency and wording are endpoint-dependent:

```text
=== reasoning_effort=no_think ===
Elapsed: <seconds>s
Reasoning characters returned: <count>
Final answer:
<answer>

=== reasoning_effort=low ===
Elapsed: <seconds>s
Reasoning characters returned: <count>
Final answer:
<answer>

=== reasoning_effort=high ===
Elapsed: <seconds>s
Reasoning characters returned: <count>
Final answer:
<answer>
```

## Interpretation

- `high` is not automatically better for simple questions.
- Deep reasoning may require more time and a larger `max_tokens` budget.
- Empty reasoning can mean `no_think`, a missing server parser, or an endpoint
  that does not expose the field separately.
- Compare final-answer correctness, not reasoning length alone.
