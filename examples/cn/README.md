# Hy3 示例代码（中文文档）

本目录提供一组可直接运行的 Python 示例的**中文说明文档**，演示如何通过 OpenAI 兼容 API 调用本地部署的腾讯混元 Hy3 模型（vLLM / SGLang）。

> 说明：本目录（`examples/cn/`）只包含中文 `.md` 文档，**不包含 `.py` 脚本**。可运行的 Python 代码统一放在 `examples/en/` 目录下（代码逻辑不分语言，中英文共用同一份脚本）。下文运行命令均通过相对路径 `../en/xxx.py` 引用对应脚本。

所有示例均通过环境变量读取连接信息，默认指向本地服务 `http://127.0.0.1:8000/v1`，模型名固定为 `hy3`。

## 示例列表

| 示例 | 说明 | 文档 | 脚本 |
| --- | --- | --- | --- |
| 01 | 单轮 / 多轮对话 | [01_basic_chat.md](01_basic_chat.md) | `../en/01_basic_chat.py` |
| 02 | 流式请求 + 逐 chunk 解析 | [02_streaming.md](02_streaming.md) | `../en/02_streaming.py` |
| 03 | 非流式 vs 流式对比（首 token 时延 / 总耗时） | [03_nonstream_vs_stream.md](03_nonstream_vs_stream.md) | `../en/03_nonstream_vs_stream.py` |
| 04 | 一次工具调用 + 多轮工具循环 | [04_tool_calling.md](04_tool_calling.md) | `../en/04_tool_calling.py` |
| 05 | 思考过程开 / 关对比 | [05_reasoning_mode.md](05_reasoning_mode.md) | `../en/05_reasoning_mode.py` |
| 06 | 超时 / 限流 / 网络错误的重试与退避 | [06_error_handling_retry.md](06_error_handling_retry.md) | `../en/06_error_handling_retry.py` |

每篇 `.md` 文档均包含三要素：**完整请求代码** + **完整 response 解析** + **一段示例输出**。

## 前置条件

- Python 3.8+
- 安装 OpenAI SDK：

  ```bash
  pip install openai
  ```

- 运行 `06_error_handling_retry` 示例还需安装 `tenacity`：

  ```bash
  pip install tenacity
  ```

- **必须先启动一个运行中的 Hy3 服务**（vLLM 或 SGLang）。服务部署方式请参考仓库根目录 README 的 [Deployment](../../README.md#deployment) 章节（vLLM / SGLang 启动命令）。默认服务地址为 `http://127.0.0.1:8000/v1`。

## 环境变量配置

所有示例通过以下环境变量读取连接信息，未设置时使用默认值：

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `HY3_BASE_URL` | `http://127.0.0.1:8000/v1` | Hy3 服务的 OpenAI 兼容 API 地址 |
| `HY3_API_KEY` | `EMPTY` | API Key，本地部署任意值均可 |

Bash 示例（Linux / macOS）：

```bash
# 使用默认本地服务
export HY3_BASE_URL="http://127.0.0.1:8000/v1"
export HY3_API_KEY="EMPTY"

# 如需指向远端或自定义端口
# export HY3_BASE_URL="http://10.0.0.10:8000/v1"
# export HY3_API_KEY="sk-xxxxxx"
```

Windows PowerShell 示例：

```powershell
$env:HY3_BASE_URL = "http://127.0.0.1:8000/v1"
$env:HY3_API_KEY = "EMPTY"
```

## 运行方式

由于 `.py` 脚本位于 `examples/en/` 目录，请在 `examples/cn/` 目录下执行以下命令运行对应脚本：

```bash
python ../en/01_basic_chat.py
python ../en/02_streaming.py
python ../en/03_nonstream_vs_stream.py
python ../en/04_tool_calling.py
python ../en/05_reasoning_mode.py
python ../en/06_error_handling_retry.py
```

也可在仓库根目录下用完整路径运行，例如：

```bash
python examples/en/01_basic_chat.py
```
