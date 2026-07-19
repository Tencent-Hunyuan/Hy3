# hy3-mcp-server

本地 MCP Server：把「读工作区文件 + 调用 Hy3」封装成工具，可在 Cline / Cursor / CodeBuddy 等客户端中使用。

场景：代码评审、本地代码与文档问答。

## 工具

| 名称 | 作用 |
|------|------|
| `list_dir` | 列出工作区内目录 |
| `read_file` | 读取工作区内文本文件 |
| `hy3_code_review` | 用 Hy3 评审代码 |
| `hy3_answer` | 结合上下文用 Hy3 回答问题 |

文件访问限制在 `HY3_MCP_ROOT` 目录内（默认进程当前目录）。

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `HY3_API_KEY` | 是 | OpenRouter 或 TokenHub 的 Key |
| `HY3_BASE_URL` | 否 | 默认 `https://openrouter.ai/api/v1`；TokenHub 用 `https://tokenhub.tencentmaas.com/v1` |
| `HY3_MODEL` | 否 | 默认 `tencent/hy3:free`；TokenHub 用 `hy3` |
| `HY3_MCP_ROOT` | 否 | 允许访问的工作区根目录 |

不要把 Key 写进仓库。可复制 `.env.example` 为 `.env` 后填写（`server.py` 会自动加载）。

## 安装

```bash
cd hy3-mcp-server
pip install -r requirements.txt
```

## 启动（stdio）

由 MCP 客户端拉起进程即可。本机手动启动示例：

```powershell
$env:HY3_API_KEY = "your-key"
$env:HY3_BASE_URL = "https://openrouter.ai/api/v1"
$env:HY3_MODEL = "tencent/hy3:free"
$env:HY3_MCP_ROOT = "C:\path\to\workspace"
python server.py
```

逻辑自检：

```bash
python smoke_test.py
```

## 客户端验证

至少两个客户端：

### 1. Cline（VS Code）

示例配置见 [`examples/cline_mcp_settings.json`](./examples/cline_mcp_settings.json)。

把 `PYTHON_EXE` / `SERVER_PY` / 工作区路径换成你的本机路径；Key 放在 `.env`，不要写进 JSON 后提交。

### 2. 命令行 MCP 客户端

```bash
python mcp_client_check.py
```

走完整 stdio 协议：`initialize` → `tools/list` → 调用 `list_dir` / `read_file` 等。看到 `PASS` 即通过。

### 其他

Cursor / CodeBuddy 配置示例见 `examples/`。也可用官方 MCP Inspector（需先 Connect，再在上方 Tools 中 List Tools）。

## 使用示例

1. `list_dir` 查看目录  
2. `read_file` 读取 `sample.py`  
3. `hy3_code_review` 评审代码  
4. `hy3_answer` 结合上下文提问  

## 演示

见 [`demo.md`](./demo.md)。

## 目录

```text
server.py
smoke_test.py
mcp_client_check.py
sample.py
requirements.txt
pyproject.toml
README.md
demo.md
.env.example
examples/
```

## 说明

- 本地 **stdio**，不要求公网部署  
- Key 仅通过环境变量 / `.env` 传入  
- 依赖官方 MCP Python SDK（`mcp`）与 OpenAI 兼容客户端  
