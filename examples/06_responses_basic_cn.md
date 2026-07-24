# 06 Responses API 基础调用

使用 Responses API 完成最小文本调用。

## 运行

```bash
uv run --env-file .env python examples/06_responses_basic.py
```

## 请求和解析

脚本通过 `client.responses.create()` 发送 `model`、`instructions`、`input` 和 `stream: false`，并从 `response.output_text` 读取最终文本。

需要处理工具或推理条目时，应进一步遍历 `response.output`。

## 输出示例

```text
我是混元，是由腾讯开发的大模型。我专注于基础信息处理与逻辑响应，支持多模态输入（文本、图片、文件等），可以帮你解答问题、创作内容、处理文件、生成代码等。如果你有具体需求，比如写作、分析、翻译等，都可以告诉我~
```

实际回答会因模型版本和采样结果变化。
