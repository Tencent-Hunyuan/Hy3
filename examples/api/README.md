# Hy3 托管 API 示例

请先完成仓库根目录的 [quickstart.md](../../quickstart.md)，再从 01 开始。01 和 02
讲基础调用，04 和 05 展示进阶能力，03 和 06 适合准备上线时阅读。

六个脚本共用 [common.py](common.py) 中的配置、流式解析、工具循环、重试和脱敏
代码。每个脚本保留本主题的完整请求和响应解析，底层逻辑只维护一份。

## 先运行基础对话

以下命令均在仓库根目录执行，需要 Python 3.10 或更新版本。

```powershell
python -m pip install -r examples/api/requirements.txt
python examples/api/01_basic_chat.py
```

确认 01 成功后，再按需运行：

```powershell
python examples/api/02_streaming.py
python examples/api/03_latency_compare.py --runs 5 --warmup 1
python examples/api/04_tool_calling.py
python examples/api/05_reasoning_mode.py
python examples/api/06_error_handling_retry.py
```

脚本只读取环境变量：

- `HY3_API_KEY`：必填，由用户提供
- `HY3_BASE_URL`：必填，必须以 `/v1` 或 `/plan/v3` 结尾
- `HY3_MODEL`：可选，默认 `hy3`
- `HY3_TIMEOUT_SECONDS`：可选，默认 60 秒
- `HY3_REASONING_MAX_TOKENS`：只用于思考模式对比，默认 4096

`.env.example` 只列出字段。脚本从当前终端或受控的秘密管理器读取环境变量，Key
应始终留在版本控制之外。

## 选择示例

| # | 主题 | 文档 |
|---|---|---|
| 01 | 基础对话：单轮、多轮和非流式响应 | [01_basic_chat.md](01_basic_chat.md) |
| 02 | 流式输出：逐块读取、usage 和中断 | [02_streaming.md](02_streaming.md) |
| 03 | 时延对比：TTFT、总耗时、P50/P95 | [03_latency_compare.md](03_latency_compare.md) |
| 04 | 工具调用：一次调用和多轮循环 | [04_tool_calling.md](04_tool_calling.md) |
| 05 | 思考模式：off/low/medium/high | [05_reasoning_mode.md](05_reasoning_mode.md) |
| 06 | 错误重试：Retry-After、退避和 jitter | [06_error_handling_retry.md](06_error_handling_retry.md) |

## 离线验证

```powershell
python -m compileall examples/api
ruff check examples/api
pytest examples/api/tests -m "not live"
```

只有本机已经安全设置 Key 时才运行：

```powershell
pytest examples/api/tests/test_live_smoke.py -m live
```

离线测试覆盖本地逻辑，live smoke 检查当前网络和账号。上述 smoke 与六个脚本已于
2026-07-17 在 TokenHub 广州入口使用 `hy3` 实测通过。输出函数会省略
response/request ID、HTTP headers 和凭据；直接使用 `print(response)` 可能暴露这些
字段。
