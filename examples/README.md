# Hy3 API Examples

[中文](#中文) | [English](#english)

---

## 中文

本目录包含 Hy3 API 的快速开始指南和 6 个完整示例，帮助开发者快速接入并使用 Hy3 API。

### 前置条件

1. 部署 Hy3 服务（参考[部署指南](../README_CN.md#推理和部署)）
2. Python 3.10+ 环境
3. 安装依赖：`pip install openai>=1.0`

### 文档

- [快速开始](./quickstart.md) — 基础信息、最小可运行示例、参数说明、常见报错排查

### 示例列表

| # | 示例 | Markdown | Python | 说明 |
|:---|:---|:---|:---|:---|
| 1 | 基础对话 | [01_basic_chat.md](./01_basic_chat.md) | [01_basic_chat.py](./01_basic_chat.py) | 单轮/多轮对话、System Prompt |
| 2 | 流式输出 | [02_streaming.md](./02_streaming.md) | [02_streaming.py](./02_streaming.py) | 流式请求、逐 chunk 解析 |
| 3 | 流式 vs 非流式 | [03_streaming_vs_non_streaming.md](./03_streaming_vs_non_streaming.md) | [03_streaming_vs_non_streaming.py](./03_streaming_vs_non_streaming.py) | 首 token 时延/总耗时对比 |
| 4 | 工具调用 | [04_tool_calling.md](./04_tool_calling.md) | [04_tool_calling.py](./04_tool_calling.py) | 单次调用、多轮工具循环、并行调用 |
| 5 | 思考模式 | [05_reasoning_mode.md](./05_reasoning_mode.md) | [05_reasoning_mode.py](./05_reasoning_mode.py) | no_think/low/high 对比 |
| 6 | 错误处理 | [06_error_handling.md](./06_error_handling.md) | [06_error_handling.py](./06_error_handling.py) | 超时/限流/网络错误重试与退避 |

### 快速运行

```bash
# 修改每个 .py 文件顶部的 BASE_URL 为你的服务地址
python examples/01_basic_chat.py
python examples/02_streaming.py
python examples/03_streaming_vs_non_streaming.py
python examples/04_tool_calling.py
python examples/05_reasoning_mode.py
python examples/06_error_handling.py
```

---

## English

This directory contains a quickstart guide and 6 complete examples for the Hy3 API.

### Prerequisites

1. Deploy Hy3 service (see [Deployment Guide](../README.md#deployment))
2. Python 3.10+ environment
3. Install dependency: `pip install openai>=1.0`

### Documentation

- [Quickstart](./quickstart.md) — Basic info, minimal runnable examples, parameter reference, troubleshooting

### Examples

| # | Example | Markdown | Python | Description |
|:---|:---|:---|:---|:---|
| 1 | Basic Chat | [01_basic_chat.md](./01_basic_chat.md) | [01_basic_chat.py](./01_basic_chat.py) | Single/multi-turn chat, System Prompt |
| 2 | Streaming | [02_streaming.md](./02_streaming.md) | [02_streaming.py](./02_streaming.py) | Streaming request, chunk parsing |
| 3 | Stream vs Non-Stream | [03_streaming_vs_non_streaming.md](./03_streaming_vs_non_streaming.md) | [03_streaming_vs_non_streaming.py](./03_streaming_vs_non_streaming.py) | TTFT & total time comparison |
| 4 | Tool Calling | [04_tool_calling.md](./04_tool_calling.md) | [04_tool_calling.py](./04_tool_calling.py) | Single call, multi-round loop, parallel calls |
| 5 | Reasoning Mode | [05_reasoning_mode.md](./05_reasoning_mode.md) | [05_reasoning_mode.py](./05_reasoning_mode.py) | no_think/low/high comparison |
| 6 | Error Handling | [06_error_handling.md](./06_error_handling.md) | [06_error_handling.py](./06_error_handling.py) | Timeout/rate-limit/network retry with backoff |

### Quick Run

```bash
# Update BASE_URL at the top of each .py file to your server address
python examples/01_basic_chat.py
python examples/02_streaming.py
python examples/03_streaming_vs_non_streaming.py
python examples/04_tool_calling.py
python examples/05_reasoning_mode.py
python examples/06_error_handling.py
```
