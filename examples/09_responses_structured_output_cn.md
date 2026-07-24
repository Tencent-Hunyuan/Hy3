# 09 Responses API 结构化输出

使用 JSON Schema 约束 Responses API 的输出格式，并将返回的 JSON 字符串解析为 Python 对象。

## 运行

```bash
uv run --env-file .env python examples/09_responses_structured_output.py
```

## 请求和解析

脚本通过 `text.format` 设置 `json_schema`，声明 `name`、`gender`、`age` 和 `city` 字段。Responses API 返回的 `response.output_text` 仍然是字符串，因此脚本使用 `json.loads()` 将其转换为 Python 字典。

## 输出示例

```json
{
  "age": 25,
  "city": "北京",
  "gender": "男",
  "name": "张三"
}
```

生产环境中应处理响应为空、请求失败和 JSON 解析异常等情况。
