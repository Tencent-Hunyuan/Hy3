# 07 Responses API 流式输出

使用 Responses API 接收 SSE 事件并逐步输出文本。

## 运行

```bash
uv run --env-file .env python examples/07_responses_streaming.py
```

## 请求和解析

请求设置 `stream: true`。脚本直接读取 SSE 的 `event` 和 `data` 行，并处理以下事件：

- `response.output_text.delta`：读取 `delta` 并拼接文本。
- `response.completed`：读取完整响应和 `usage`。
- `response.failed`：抛出错误并终止请求。

当前 TokenHub 的 `response.created` 事件可能返回 `output: null`，部分 OpenAI SDK 版本的高层 Responses 流解析器会因此报错，所以该示例使用 Python 标准库解析原始 SSE。

## 输出示例

```text
深圳是中国南部滨海的现代化大都市，也是粤港澳大湾区的核心引擎之一。它以“改革开放窗口”闻名，从昔日小渔村快速发展为全球科技创新与金融重镇。这里拥有华为、腾讯等顶尖企业，兼具活力多元的城市文化与优美的自然海岸风光。

usage: {'input_tokens': 21, 'output_tokens': 58, 'total_tokens': 79}
```
