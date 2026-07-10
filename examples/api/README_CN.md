# Hy3 API 示例

[English](README.md) · [API 快速开始](../../quickstart_CN.md) · [项目 README](../../README_CN.md)

## 安装

从仓库根目录运行：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r examples/api/requirements.txt
cp examples/api/.env.example examples/api/.env
```

在 Windows PowerShell 中，使用 `.\.venv\Scripts\Activate.ps1` 激活，并用 `Copy-Item examples/api/.env.example examples/api/.env` 复制模板。

可以直接使用 `.env.example` 中的自部署默认值，也可以按照 [API 快速开始](../../quickstart_CN.md#api-配置)配置 OpenRouter。不要提交真实 API key。

## 环境变量

| 变量 | 自部署默认值 | OpenRouter |
|---|---|---|
| `HY3_BACKEND` | `self_hosted` | `openrouter` |
| `HY3_BASE_URL` | `http://127.0.0.1:8000/v1` | `https://openrouter.ai/api/v1` |
| `HY3_API_KEY` | `EMPTY` | 从环境变量读取 |
| `HY3_MODEL` | `hy3` | `tencent/hy3:free` |
| `HY3_TIMEOUT` | `120` | 有限正数 |

`common.py` 负责读取 `examples/api/.env`、校验配置、创建 OpenAI client、映射推理参数，并规范化各示例共用的响应字段。

## 学习路径

从仓库根目录依次运行。每份指南都包含完整请求、响应解析、确定性离线输出和限制说明。

| 顺序 | 脚本 | 指南 | 学习内容 |
|---|---|---|---|
| 1 | [`01_basic_chat.py`](01_basic_chat.py) | [基础对话](01_basic_chat_CN.md) / [English](01_basic_chat.md) | 单轮请求、assistant 历史和规范化响应字段。 |
| 2 | [`02_streaming.py`](02_streaming.py) | [流式输出](02_streaming_CN.md) / [English](02_streaming.md) | 空 chunk、仅 usage chunk、content/reasoning 分离和工具调用分片。 |
| 3 | [`03_streaming_vs_non_streaming.py`](03_streaming_vs_non_streaming.py) | [流式与非流式对比](03_streaming_vs_non_streaming_CN.md) / [English](03_streaming_vs_non_streaming.md) | 相同采样下的首次输出、首次可见 content 和总耗时。 |
| 4 | [`04_tool_calling.py`](04_tool_calling.py) | [工具调用](04_tool_calling_CN.md) / [English](04_tool_calling.md) | 同一 assistant 回合返回多个调用、顺序执行、assistant/tool 历史、结构化错误和有界轮次。 |
| 5 | [`05_reasoning_mode.py`](05_reasoning_mode.py) | [推理模式](05_reasoning_mode_CN.md) / [English](05_reasoning_mode.md) | 同一问题下 `no_think` 与 `high` 的后端映射对比。 |
| 6 | [`06_error_handling_retry.py`](06_error_handling_retry.py) | [错误处理与重试](06_error_handling_retry_CN.md) / [English](06_error_handling_retry.md) | 禁用 SDK 重试、应用层策略、Retry-After、jitter 和离线模拟。 |

命令：

```bash
python examples/api/01_basic_chat.py
python examples/api/02_streaming.py
python examples/api/03_streaming_vs_non_streaming.py --warmup
python examples/api/04_tool_calling.py
python examples/api/05_reasoning_mode.py
python examples/api/06_error_handling_retry.py --simulate
```

前五个命令以及不带 `--simulate` 的重试脚本需要配置后端。`--simulate` 模式是确定性的，不需要 API 配置或网络。
