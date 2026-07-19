# Hy3 示例代码（中文）

通过 OpenAI 兼容 API 调用腾讯混元 **Hy3** 的可运行示例集合。

支持：

- **腾讯云 TokenHub** — 设置 `HY3_BASE_URL=https://tokenhub.tencentmaas.com/v1` 与 API Key
- **本地 vLLM / SGLang** — 默认 `http://127.0.0.1:8000/v1`，`api_key=EMPTY`

每个示例均提供 **`.py` + `.md` + `.ipynb`**。共享工具见 [`../common.py`](../common.py)。英文版：[`../en/`](../en/)。

## 示例列表

| 示例 | 说明 | 文件 |
| --- | --- | --- |
| `01_basic_chat` | 单轮 / 多轮对话 | [py](01_basic_chat.py) · [md](01_basic_chat.md) · [ipynb](01_basic_chat.ipynb) |
| `02_streaming` | 流式请求 + 逐 chunk 解析 | [py](02_streaming.py) · [md](02_streaming.md) · [ipynb](02_streaming.ipynb) |
| `03_nonstream_vs_stream` | 首 token 时延 / 总耗时对比 | [py](03_nonstream_vs_stream.py) · [md](03_nonstream_vs_stream.md) · [ipynb](03_nonstream_vs_stream.ipynb) |
| `04_tool_calling` | 一次工具调用 + 有界多轮工具循环 | [py](04_tool_calling.py) · [md](04_tool_calling.md) · [ipynb](04_tool_calling.ipynb) |
| `05_reasoning_mode` | `no_think` / `low` / `high` 对比 | [py](05_reasoning_mode.py) · [md](05_reasoning_mode.md) · [ipynb](05_reasoning_mode.ipynb) |
| `06_error_handling_retry` | 超时 / 429 / 网络错误重试与退避 | [py](06_error_handling_retry.py) · [md](06_error_handling_retry.md) · [ipynb](06_error_handling_retry.ipynb) |

每篇 `.md` 均包含：**完整请求代码** + **完整 response 解析** + **一段示例输出**。

## 前置条件

```bash
pip install -r examples/requirements.txt
```

离线单元测试（无需 API Key）：

```bash
pip install -r examples/requirements-dev.txt
pytest examples/tests -q
```

- **TokenHub：** 创建 API Key 即可，无需 GPU。
- **本地：** 先按根目录 [README 部署](../../README_CN.md#推理和部署) 启动 Hy3。工具调用 / 思考字段需开启 quickstart 中说明的解析器。

## 环境变量

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `HY3_BASE_URL` | `http://127.0.0.1:8000/v1` | OpenAI 兼容 API 地址 |
| `HY3_API_KEY` | `EMPTY` | API Key |
| `HY3_MODEL` | `hy3` | 模型名 |
| `HY3_TIMEOUT` | `120` | 客户端超时（秒） |

模板：[`../.env.example`](../.env.example)。

```bash
# 本地
export HY3_BASE_URL="http://127.0.0.1:8000/v1"
export HY3_API_KEY="EMPTY"

# TokenHub
# export HY3_BASE_URL="https://tokenhub.tencentmaas.com/v1"
# export HY3_API_KEY="sk-xxxxxxxx"
```

Windows PowerShell：

```powershell
$env:HY3_BASE_URL = "http://127.0.0.1:8000/v1"
$env:HY3_API_KEY = "EMPTY"
```

## 运行方式

在仓库根目录执行：

```bash
python examples/cn/01_basic_chat.py
python examples/cn/02_streaming.py
python examples/cn/03_nonstream_vs_stream.py
python examples/cn/04_tool_calling.py
python examples/cn/05_reasoning_mode.py
python examples/cn/06_error_handling_retry.py
```

也可在 Jupyter / VS Code 中打开对应 `.ipynb`。

## 设计说明

- **双端兼容思考开关：** 示例同时发送 TokenHub 的 `thinking` 与本地的 `chat_template_kwargs.reasoning_effort`（见 `common.build_extra_body`）。
- **有界工具循环与重试：** 限制最大轮数 / 最大尝试次数 / 总等待时间，避免演示脚本挂死。
- **仓库不含密钥：** Key 仅通过环境变量注入；示例输出为代表性或脱敏文本。

另见：[quickstart_CN.md](../../quickstart_CN.md)。
