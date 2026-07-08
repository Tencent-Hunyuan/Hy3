# Hy3 Docx Assistant MCP Server

基于 MCP（Model Context Protocol）的本地 stdio MCP Server，封装 Hy3 推理能力，面向 Word 文档办公场景，支持 CodeBuddy / WorkBuddy / Cursor / Cline 即插即用。

## 完成内容

- 基于 MCP Python SDK（`FastMCP`）提供本地 stdio MCP Server。
- 暴露 3 个 Hy3 tool：
  - `read_docx`：读取 `.docx`，让 Hy3 做摘要或针对文档问答。
  - `edit_docx_by_instruction`：按自然语言指令重写非空段落，输出 `<name>.hy3-edited.docx`（原文件不改）。
  - `suggest_docx_comments`：让 Hy3 生成审阅意见，并写入**真实 Word 批注**到 `<name>.comments.docx`。
- 通过 `HY3_BASE_URL` / `HY3_API_KEY` / `HY3_MODEL` 调用 Hy3 OpenAI-compatible API，**不硬编码 Key**。
- 提供 CodeBuddy/WorkBuddy 与 Cursor 的 MCP 配置示例。
- 兼容任意 OpenAI 兼容端点（本地 vLLM/SGLang 部署 Hy3，或 DeepSeek 等），方便无密钥环境 smoke test。

## 配置

```bash
pip install -e .
# 安装后命令：docx-assistant-mcp
```

环境变量：

| 变量 | 说明 | 默认 |
|---|---|---|
| `HY3_BASE_URL` | Hy3 OpenAI 兼容端点 | `http://127.0.0.1:8000/v1` |
| `HY3_API_KEY` | API Key（本地无鉴权用 `EMPTY`） | `EMPTY` |
| `HY3_MODEL` | 模型名 | `hy3` |
| `HY3_REASONING_EFFORT` | Hy3 推理强度：`no_think`/`low`/`high` | `no_think` |
| `HY3_SEND_REASONING_EFFORT` | 是否发送 Hy3 专属 `reasoning_effort` 参数（非 Hy3 端点设 `false`） | `true` |

MCP 配置示例（CodeBuddy/WorkBuddy 用 `~/.workbuddy/.mcp.json`，Cursor 用 `~/.cursor/mcp.json`）：

```json
{
  "mcpServers": {
    "hy3-docx-assistant": {
      "command": "docx-assistant-mcp",
      "env": {
        "HY3_BASE_URL": "http://127.0.0.1:8000/v1",
        "HY3_API_KEY": "EMPTY",
        "HY3_MODEL": "hy3"
      }
    }
  }
}
```

## 验证

```bash
pip install -e .
python -m compileall src
```

在 MCP 客户端中调用 `examples/sample.docx`：

- 「总结这篇文档并给 5 条改进建议」→ `read_docx`
- 「改成正式项目报告风格」→ `edit_docx_by_instruction`
- 「审一下，聚焦逻辑与清晰度」→ `suggest_docx_comments`（生成 `sample.comments.docx`，用 Word 打开可见真实批注）

## 备注

- 真实 Hy3 调用需配置可用的 Hy3 API endpoint；DeepSeek 等兼容端点仅用于本地 smoke test 与演示。
- 代码中无硬编码 Key，所有密钥经环境变量传入。
