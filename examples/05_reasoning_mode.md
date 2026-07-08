<p align="left">
    <a href="./zh-cn/05_reasoning_mode.md">中文</a>&nbsp;｜&nbsp;English
</p>
<br>

# Example 05: Reasoning mode

This example compares `reasoning_effort="no_think"` and `reasoning_effort="high"`.

> Related: [Examples Index](./README.md) | [API Quickstart](../quickstart.md)

## Run

```bash
python examples/05_reasoning_mode.py
```

## Full request

```python
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "一个水池有进水管和出水管..."}],
    temperature=0.2,
    max_tokens=900,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}},
)
```

Equivalent HTTP body:

```json
{
  "model": "hy3",
  "messages": [
    {"role": "user", "content": "一个水池有进水管和出水管。进水管 6 小时注满，出水管 9 小时放空。两管同时开，多久注满？请给出答案。"}
  ],
  "temperature": 0.2,
  "max_tokens": 900,
  "chat_template_kwargs": {"reasoning_effort": "high"}
}
```

## Response parsing

```python
message = response.choices[0].message
answer = message.content
reasoning_content = getattr(message, "reasoning_content", None)
```

If `reasoning_content` is absent, the server may not have launched with a reasoning parser, or it may not expose reasoning separately.

## Sample output

```text
=== reasoning_effort=no_think ===
elapsed_s: 1.942
answer:
两管同时开时，净注水速度为 1/6 - 1/9 = 1/18 个水池/小时，因此 18 小时注满。
reasoning_content_detected: no
usage: CompletionUsage(...)

=== reasoning_effort=high ===
elapsed_s: 4.815
answer:
答案是 18 小时。进水管每小时注入 1/6 个水池，出水管每小时放出 1/9 个水池，净速度为 1/18 个水池/小时，所以注满需要 18 小时。
reasoning_content_detected: yes
reasoning_preview: [reasoning content omitted/truncated in docs] ...
usage: CompletionUsage(...)
```
