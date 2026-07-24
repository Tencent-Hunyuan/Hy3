# 09 Responses API structured output

Constrain the output with JSON Schema and parse the returned JSON string.

```bash
uv run --env-file .env python examples/09_responses_structured_output.py
```

The script configures `text.format` with `json_schema`, reads `response.output_text`, and calls `json.loads()` to convert the string into a Python dictionary. Production code should handle empty responses, request failures, and JSON parsing errors.

## Output example

Observed structured output:

```json
{
  "age": 25,
  "city": "北京",
  "gender": "男",
  "name": "张三"
}
```

English interpretation: `age` is 25, `city` is Beijing, `gender` is male, and `name` is Zhang San. The JSON keys are defined by the schema; values may vary with the input.
