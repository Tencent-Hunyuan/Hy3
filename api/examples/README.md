# Hy3 API examples

先完成[快速开始](../quickstart.md)中的安装和环境变量配置。所有脚本都可以从仓库根目录独立运行，并使用同一套环境变量。

| 示例 | 能力 | 文档 |
|---|---|---|
| 01 | 单轮与多轮对话 | [basic chat](01_basic_chat/README.md) |
| 02 | 流式请求与逐 chunk 解析 | [streaming](02_streaming/README.md) |
| 03 | 首 token 时延与总耗时 | [latency comparison](03_latency_comparison/README.md) |
| 04 | 一次调用与多轮工具循环 | [tool calling](04_tool_calling/README.md) |
| 05 | 思考模式开关对比 | [reasoning mode](05_reasoning_mode/README.md) |
| 06 | 超时、限流、网络错误重试 | [error handling](06_error_handling_retry/README.md) |

文档中的响应 ID、token 数和时延是示例值，实际结果会因输入、服务负载和采样而变化。
