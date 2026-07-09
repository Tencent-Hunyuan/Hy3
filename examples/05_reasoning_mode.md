# 05 Reasoning Mode

This example compares two Hy3 reasoning settings with the same math question.

Script: [05_reasoning_mode.py](05_reasoning_mode.py)

## Complete Request

The script sends the same prompt twice and only changes `reasoning_effort`:

```python
prompt = "A train travels 120 km in 1.5 hours. What is its average speed?"

for effort in ["no_think", "high"]:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
        top_p=1.0,
        extra_body={"chat_template_kwargs": {"reasoning_effort": effort}},
    )
```

Use `no_think` for direct answers. Use a stronger mode such as `high` when your serving template supports more deliberate reasoning.

## Complete Response Parsing

Each call is non-streaming, so the final assistant text is read from:

```python
print(response.choices[0].message.content)
```

Response shape:

```text
response
└── choices[0]
    └── message
        └── content = answer for the selected reasoning mode
```

## Run

```bash
python examples/05_reasoning_mode.py
```

## Example Output

```text
=== reasoning_effort=no_think ===
The average speed is 80 km/h.

=== reasoning_effort=high ===
Average speed equals distance divided by time: 120 km / 1.5 h = 80 km/h. So the train's average speed is 80 km/h.
```

Exact wording can vary. The important part is that both calls solve the same question while using different `reasoning_effort` values.
