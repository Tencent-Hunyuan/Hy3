# 在 Cursor 中使用 / Using hy3-security-mcp in Cursor

## 前置条件 / Prerequisites

- Python ≥ 3.11,以及 `uv`/`uvx`(或 `pip install .` 到某个环境)。
- 一个 Hy3 API key(见仓库根目录 [`.env.example`](../../.env.example) 的三种后端选项)。
- Cursor(支持 MCP 的版本)。

Python ≥ 3.11, plus `uv`/`uvx` (or `pip install .` into some environment). A Hy3 API key (see the repo root [`.env.example`](../../.env.example)). A recent version of Cursor with MCP support.

## 配置 `mcp.json` / Configure `mcp.json`

Cursor 从 `.cursor/mcp.json`(项目级)或 `~/.cursor/mcp.json`(全局)读取 MCP server 配置,顶层 key 为 `mcpServers`;stdio server 用 `type: "stdio"` + `command`/`args`/`env`。Cursor 的 `env` 支持 `${env:VAR_NAME}` 语法,从启动 Cursor 的宿主环境里取值,因此配置文件本身不含真实密钥即可提交(参考:[Cursor MCP 文档](https://cursor.com/docs/context/mcp))。

Cursor reads MCP server config from `.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global); the top-level key is `mcpServers`, and stdio servers use `type: "stdio"` plus `command`/`args`/`env`. Cursor's `env` supports `${env:VAR_NAME}` expansion from the host environment, so the file itself can be committed without a real secret (reference: [Cursor MCP docs](https://cursor.com/docs/context/mcp)).

在项目根目录创建 `.cursor/mcp.json`(内容同 [`examples/cursor.mcp.json`](../../examples/cursor.mcp.json)):

Create `.cursor/mcp.json` at the project root (same content as [`examples/cursor.mcp.json`](../../examples/cursor.mcp.json)):

```json
{
  "mcpServers": {
    "hy3-security-mcp": {
      "type": "stdio",
      "command": "uvx",
      "args": ["hy3-security-mcp"],
      "env": {
        "HY3_BASE_URL": "https://openrouter.ai/api/v1",
        "HY3_API_KEY": "${env:HY3_API_KEY}",
        "HY3_MODEL": "tencent/hy3:free"
      }
    }
  }
}
```

尚未发布到 PyPI 时,把 `"args": ["hy3-security-mcp"]` 换成本地检出路径:`"args": ["--from", "/absolute/path/to/hy3-security-mcp", "hy3-security-mcp"]`。

Until published to PyPI, replace `"args": ["hy3-security-mcp"]` with a local-checkout form: `"args": ["--from", "/absolute/path/to/hy3-security-mcp", "hy3-security-mcp"]`.

确保启动 Cursor 的环境里已设置 `HY3_API_KEY`(例如通过 shell profile,或 macOS 上用 `launchctl setenv`,再重启 Cursor)。

Make sure `HY3_API_KEY` is set in the environment Cursor itself launches from (e.g. via your shell profile, or `launchctl setenv` on macOS, then restart Cursor).

## 验证连接 / Verify the connection

打开 Cursor 设置里的 MCP 面板(**Settings → Cursor Settings → MCP**,不同版本命名可能略有差异),`hy3-security-mcp` 应显示为已连接,并可展开看到 4 个工具:`audit_command`、`review_diff`、`scan_secrets`、`vuln_intel`。

Open the MCP panel in Cursor's settings (**Settings → Cursor Settings → MCP**, naming may vary slightly by version); `hy3-security-mcp` should show as connected, expandable to the 4 tools: `audit_command`, `review_diff`, `scan_secrets`, `vuln_intel`.

## 端到端演示 / End-to-end demo

在 Cursor 的 Agent/Chat 里输入:

In Cursor's Agent/Chat panel:

> 请使用 audit_command 工具审计这条命令是否安全:`rm -rf /`
>
> Use the audit_command tool to check whether this command is safe: `rm -rf /`

预期结果(确定性快速路径拦截,无 LLM/网络调用):

Expected result (caught by the deterministic fast path, no LLM/network call):

```json
{
  "level": "deny",
  "category": "destructive_fs",
  "rationale": "快速路径拦截:rm -rf 指向根目录/系统路径/家目录,递归删除不可逆",
  "safer_alternative": null,
  "source": "fast_path"
}
```
