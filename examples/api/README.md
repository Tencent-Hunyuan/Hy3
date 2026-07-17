# Hy3 Hosted API examples

这 6 个脚本共享 [common.py](common.py) 中的配置、流式聚合、工具循环、重试和脱敏
逻辑，但每个脚本都保留本主题的完整请求与响应解析。请先完成仓库根目录的
[quickstart.md](../../quickstart.md)。

除专门展开策略的 06 外，其余 Hosted 请求统一经过 `create_chat_completion`：SDK
内建重试保持关闭，由公共代码对文档列出的临时错误执行有上限的显式重试。

## 安装与运行

```powershell
python -m pip install -r examples/api/requirements.txt
python examples/api/01_basic_chat.py
python examples/api/02_streaming.py
python examples/api/03_latency_compare.py --runs 5 --warmup 1
python examples/api/04_tool_calling.py
python examples/api/05_reasoning_mode.py
python examples/api/06_error_handling_retry.py
```

所有配置只来自环境变量：

- `HY3_API_KEY`：必填，无默认值，placeholder 会被拒绝；
- `HY3_BASE_URL`：必填，必须以 `/v1` 或 `/plan/v3` 结尾；
- `HY3_MODEL`：默认 `hy3`；
- `HY3_TIMEOUT_SECONDS`：默认 60；
- `HY3_REASONING_MAX_TOKENS`：仅 reasoning 对比使用，默认 4096。

`.env.example` 只是字段模板，脚本不会自动读取 `.env`；请在当前终端或受控的秘密
管理器中注入变量，避免无意提交 Key。

## 示例索引

| # | 主题 | 文档 |
|---|---|---|
| 01 | 单轮/多轮与完整非流式解析 | [01_basic_chat.md](01_basic_chat.md) |
| 02 | 流式 delta、空 choices、usage 尾块与中断 | [02_streaming.md](02_streaming.md) |
| 03 | 重复采样的 TTFT/总耗时与 P50/P95 | [03_latency_compare.md](03_latency_compare.md) |
| 04 | 单次 tool call 与有上限的多轮工具循环 | [04_tool_calling.md](04_tool_calling.md) |
| 05 | thinking off/low/medium/high | [05_reasoning_mode.md](05_reasoning_mode.md) |
| 06 | 临时错误、Retry-After、退避与 jitter | [06_error_handling_retry.md](06_error_handling_retry.md) |

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

离线 mock 通过不代表当前网络和账号一定可用。上述 smoke 与六个脚本已在
2026-07-17 使用 TokenHub 广州 `hy3` 实测通过；输出函数故意省略
response/request ID、HTTP headers 和凭据，不要用 `print(response)` 替代它。
