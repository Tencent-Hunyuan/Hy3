# Hy3 API Examples

这组示例使用 OpenAI Python SDK 调用 Hy3 的 OpenAI 兼容 Chat Completions API。每个示例都可单独运行，并配有完整请求说明、响应解析和示例输出。

## 准备环境

```bash
cd examples/api
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

编辑 `.env`，填入真实 `HY3_API_KEY`。`.env` 已被仓库忽略，不要把密钥提交到 Git。

默认配置：

```text
HY3_BASE_URL=https://tokenhub.tencentmaas.com/v1
HY3_MODEL=hy3
```

## 示例索引

| 用时 | 示例 | 能力 |
| --- | --- | --- |
| 3 分钟 | [01 Basic chat](01_basic_chat.md) | 单轮、多轮对话和完整响应字段 |
| 4 分钟 | [02 Streaming](02_streaming.md) | 逐 chunk 解析 content、reasoning、finish reason 和 usage |
| 4 分钟 | [03 Latency comparison](03_latency_comparison.md) | 首个可见 chunk 时延与总耗时 |
| 8 分钟 | [04 Tool calling](04_tool_calling.md) | JSON Schema、工具分发和有上限的多轮循环 |
| 4 分钟 | [05 Reasoning mode](05_reasoning_mode.md) | 思考模式开关与推理强度 |
| 6 分钟 | [06 Error handling](06_error_handling_retry.md) | 超时、网络、429 和 5xx 的有限退避重试 |

直接运行：

```bash
python 01_basic_chat.py
python 02_streaming.py
python 03_latency_comparison.py
python 04_tool_calling.py
python 05_reasoning_mode.py
python 06_error_handling_retry.py
```

## 配置自托管服务

如果已经按仓库根 README 启动 vLLM 或 SGLang，可在 `.env` 中改为：

```text
HY3_BASE_URL=http://127.0.0.1:8000/v1
HY3_API_KEY=EMPTY
HY3_MODEL=hy3
```

这些示例的思考模式参数针对 TokenHub。自托管服务请参考根 README 中的 `chat_template_kwargs.reasoning_effort` 配置。

## 离线测试

测试使用标准库 `unittest` 和模拟响应，不发送网络请求：

```bash
python -m unittest discover -s tests -v
```

配置真实 Key 后，可显式启用最小 live smoke test：

```bash
HY3_RUN_LIVE_TESTS=1 python -m unittest discover -s tests -p 'test_live_smoke.py' -v
```

## 安全提示

- 只通过环境变量或未跟踪的 `.env` 文件加载 API Key。
- 工具调用必须采用函数白名单，并验证模型生成的参数。
- 对外日志应删除 API Key、业务敏感输入和未脱敏的响应内容。
- 超时重试可能重复产生请求和费用，应限制尝试次数。
