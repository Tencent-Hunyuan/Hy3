# Demos — 演示

## MCP 客户端实录 GIF / Recorded MCP-client session

![hy3-security-mcp MCP stdio demo](hy3-security-mcp-demo.gif)

上图是一次**真实 MCP 会话**的录屏：一个最小 MCP 客户端（[`examples/mcp_stdio_client_demo.py`](../../examples/mcp_stdio_client_demo.py)）通过 **stdio 传输**连上 `hy3-security-mcp` 服务器——与 Cursor / CodeBuddy / Cline 走的是同一套 MCP 协议——完成握手、`list_tools`、并依次调用工具：`audit_command`（确定性快路径 deny + 包装/别名规避仍被拦 + LLM 裁决 confirm）与 `scan_secrets`（原文密钥脱敏后再分诊）。画面里的 `server.py … Processing request of type CallToolRequest` 是服务器真实处理每一次 MCP 请求的日志。

The GIF is a real MCP session: a minimal MCP client connects to the `hy3-security-mcp` server over the **stdio transport** — the same MCP protocol Cursor / CodeBuddy / Cline use — and performs the handshake, `list_tools`, and real tool calls. The `server.py … Processing request of type CallToolRequest` lines are the server actually handling each MCP request.

> 这满足 issue 的「在 MCP 客户端中实际调用 Server」要求：驱动脚本本身就是一个符合协议的 MCP 客户端。IDE 接入见 [`../clients/`](../clients/)。
> This satisfies the issue's "actually invoke the server in an MCP client" requirement — the driver *is* a protocol-conformant MCP client. For IDE setup see [`../clients/`](../clients/).

### 复现 / Reproduce

```bash
# 1) 直接跑驱动（任意 MCP-capable 环境都可，需 HY3_API_KEY 见 ../../.env.example）
uv run python examples/mcp_stdio_client_demo.py

# 2) 重新录制 GIF —— 两种方式任选：
#    a. asciinema + agg（本仓所用，无需图形界面）
env HY3_API_KEY=... DEMO_PACE_SECONDS=1.1 COLUMNS=100 \
  asciinema rec docs/demos/demo.cast --overwrite \
  --command "uv run python examples/mcp_stdio_client_demo.py"
agg docs/demos/demo.cast docs/demos/hy3-security-mcp-demo.gif \
  --font-size 15 --theme monokai --cols 100 --rows 34 --idle-time-limit 1.4
#    b. VHS（需 ttyd + Chrome）: env HY3_API_KEY=... vhs docs/demos/demo.tape
```

API key 只经环境变量传入，不出现在 `demo.tape` / `demo.cast` / GIF 中。
The API key is passed via environment only; it never appears in `demo.tape` / `demo.cast` / the GIF.

## 文字实录（含全部 4 工具）/ Full text transcript (all 4 tools)

[`live-cli-demo.md`](live-cli-demo.md) — 一次真实运行的完整 JSON 输出，额外覆盖 `review_diff`（命令注入检出）与 `vuln_intel`（真实 OSV.dev 查询 + Hy3 综合），后两者评测语料未涉及。
A real run's full JSON output, additionally covering `review_diff` and `vuln_intel` (a live OSV.dev query + Hy3 synthesis) which the eval corpus does not exercise.
