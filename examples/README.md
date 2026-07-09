# Hy3 示例代码

本目录提供一组可直接运行的 Python 示例，演示如何通过 OpenAI 兼容 API 调用本地部署的腾讯混元 Hy3 模型（vLLM / SGLang）。

所有示例均通过环境变量读取连接信息，默认指向本地服务 `http://127.0.0.1:8000/v1`，模型名固定为 `hy3`。

## 示例列表

| 示例 | 说明 |
| --- | --- |
| `01_basic_chat` | 单轮 / 多轮对话 |
| `02_streaming` | 流式请求 + 逐 chunk 解析 |
| `03_nonstream_vs_stream` | 非流式 vs 流式对比（首 token 时延 / 总耗时） |
| `04_tool_calling` | 一次工具调用 + 多轮工具循环 |
| `05_reasoning_mode` | 思考过程开 / 关对比 |
| `06_error_handling_retry` | 超时 / 限流 / 网络错误的重试与退避 |

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

- **必须先启动一个运行中的 Hy3 服务**（vLLM 或 SGLang）。服务部署方式请参考仓库根目录 README 的 [Deployment](../README.md#deployment) 章节（vLLM / SGLang 启动命令）。默认服务地址为 `http://127.0.0.1:8000/v1`。

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

在仓库根目录下执行（推荐），或在 `examples/` 目录下执行：

```bash
python examples/01_basic_chat.py
python examples/02_streaming.py
python examples/03_nonstream_vs_stream.py
python examples/04_tool_calling.py
python examples/05_reasoning_mode.py
python examples/06_error_handling_retry.py
```

每个示例目录下均配有同名的 `.md` 说明文档（中文），包含完整请求代码、response 解析与示例输出。
