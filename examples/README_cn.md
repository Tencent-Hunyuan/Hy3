<p align="left">
   <a href="../quickstart.md">English</a> ｜ 中文
</p>

# Hy3 API 示例

本目录提供可直接运行的 Python 示例，覆盖腾讯云 TokenHub 的 Chat Completions API 和 Responses API。

示例统一使用 Python 文件，配套说明集中在本文档中。`.py` 文件便于直接运行、复用和后续加入自动化检查。

## 运行前提

在仓库根目录创建 `.env`，或在当前终端设置环境变量：

```bash
export HY3_API_KEY="你的 TokenHub API Key"
export HY3_BASE_URL="https://tokenhub.tencentmaas.com/v1"
```

安装依赖：

```bash
uv sync
```

从仓库根目录运行示例：

```bash
uv run --env-file .env python examples/02_streaming.py
```

如果不使用 `.env`，可以省略 `--env-file .env`。API Key 不应写入 Python 文件，也不应提交 `.env`。

## 示例列表

| 文件                                                                             | 内容                                                |
|--------------------------------------------------------------------------------|---------------------------------------------------|
| [`01_basic_chat.py`](01_basic_chat.py)                                   | Chat Completions 单轮调用，作为最小入门示例。                   |
| [`02_streaming.py`](02_streaming.py)                                     | Chat Completions 流式输出，处理空 `delta` 和最终 `usage`。    |
| [`03_streaming_vs_non_streaming.py`](03_streaming_vs_non_streaming.py)   | 对比 Chat Completions 非流式和流式请求的响应耗时。                |
| [`04_tool_calling.py`](04_tool_calling.py)                               | Chat Completions 函数工具调用，执行本地函数并循环回传工具结果。          |
| [`05_reasoning_mode.py`](05_reasoning_mode.py)                           | 对比 Chat Completions 关闭和开启推理模式时的请求与响应。             |
| [`06_responses_basic.py`](06_responses_basic.py)                         | Responses API 最小调用示例，读取 `response.output_text`。   |
| [`07_responses_streaming.py`](07_responses_streaming.py)                 | Responses API 流式输出示例，解析文本增量事件。                    |
| [`08_responses_tool_calling.py`](08_responses_tool_calling.py)           | Responses API 函数工具调用示例，回传 `function_call_output`。 |
| [`09_responses_structured_output.py`](09_responses_structured_output.py) | Responses API 结构化输出示例，并解析 JSON 字符串。               |
| [`10_error_handling_retry.py`](10_error_handling_retry.py)               | 连接错误、超时、限流和服务端错误的指数退避重试。                          |

每个脚本均有同名中文说明文档，例如 [`01_basic_chat_cn.md`](01_basic_chat_cn.md)。说明文档包含运行命令、请求和响应解析方式以及一次实际运行的输出示例。

示例中的天气函数仅用于演示工具调用流程，不会访问真实天气服务。

`07_responses_streaming.py` 使用标准库直接解析 SSE 事件。这是因为当前 TokenHub 的 `response.created` 事件可能返回 `output: null`，部分 OpenAI SDK 版本的 Responses 高层流式解析器会假设该字段始终为数组，从而触发解析异常。

## 说明

示例输出可能因模型版本、服务负载和随机采样而变化。参数和协议支持范围以 [Hy3 调用指南](https://cloud.tencent.com/document/product/1823/132252) 及 [TokenHub 语言模型调用概览](https://cloud.tencent.com/document/product/1823/130079) 为准。
