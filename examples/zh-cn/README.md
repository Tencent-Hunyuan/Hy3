<p align="left">
    <a href="../README.md">English</a>&nbsp;｜&nbsp;中文
</p>
<br>

# Hy3 API 示例

这些示例展示 Hy3 兼容 OpenAI API 的常见调用方式。如果还没有配置客户端环境，请先阅读 [API 快速开始](../../quickstart_CN.md)。

## 环境准备

在仓库根目录安装客户端依赖：

```bash
python -m pip install -r requirements.txt
```

设置服务连接变量：

```bash
export HY3_BASE_URL="${HY3_BASE_URL:-http://127.0.0.1:8000/v1}"
export HY3_API_KEY="${HY3_API_KEY:-EMPTY}"
export HY3_MODEL="${HY3_MODEL:-hy3}"
```

## 示例索引

| 说明文档 | 示例脚本 | 演示内容 |
| --- | --- | --- |
| [01. 基础聊天](01_basic_chat.md) | [`01_basic_chat.py`](01_basic_chat.py) | 单轮和多轮聊天。 |
| [02. 流式输出](02_streaming.md) | [`02_streaming.py`](02_streaming.py) | 流式请求和逐 chunk 解析。 |
| [03. 延迟对比](03_latency_compare.md) | [`03_latency_compare.py`](03_latency_compare.py) | 非流式总延迟与流式首 token 延迟、总延迟对比。 |
| [04. 工具调用](04_tool_calling.md) | [`04_tool_calling.py`](04_tool_calling.py) | 单次工具调用响应和应用侧多轮工具执行循环。 |
| [05. 推理模式](05_reasoning_mode.md) | [`05_reasoning_mode.py`](05_reasoning_mode.py) | `no_think` 与 `high` 推理模式行为对比。 |
| [06. 错误处理与重试](06_error_handling_retry.md) | [`06_error_handling_retry.py`](06_error_handling_retry.py) | 超时、限流、网络错误和可重试服务端错误处理。 |

请在仓库根目录运行脚本，例如：

```bash
python examples/zh-cn/01_basic_chat.py
```
