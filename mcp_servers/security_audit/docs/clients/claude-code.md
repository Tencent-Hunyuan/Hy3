# 在 Claude Code 中使用 / Using hy3-security-mcp in Claude Code

## 前置条件 / Prerequisites

- Python ≥ 3.11,以及 `uv`/`uvx`(或 `pip install .` 到某个环境)。
- 一个 Hy3 API key(见仓库根目录 [`.env.example`](../../.env.example) 的三种后端选项:OpenRouter `tencent/hy3:free` 免费起步 / 腾讯云混元 / 本地 vLLM)。
- Claude Code CLI(`claude`)。

Python ≥ 3.11, plus `uv`/`uvx` (or `pip install .` into some environment). A Hy3 API key (see the repo root [`.env.example`](../../.env.example) for the three backend options). The Claude Code CLI (`claude`).

## 方式一:CLI 添加 / Option 1: `claude mcp add`

```bash
# 项目级(写入仓库根目录的 .mcp.json,team 可共享)/ project scope (writes .mcp.json at repo root, shareable with the team)
claude mcp add --scope project \
  --env HY3_BASE_URL=https://openrouter.ai/api/v1 \
  --env HY3_API_KEY="$HY3_API_KEY" \
  --env HY3_MODEL=tencent/hy3:free \
  -- uvx --from /absolute/path/to/hy3-security-mcp hy3-security-mcp
```

一旦 `hy3-security-mcp` 发布到 PyPI,`--` 之后可简化为 `uvx hy3-security-mcp`(不再需要 `--from`)。

Once `hy3-security-mcp` is published to PyPI, the command after `--` simplifies to `uvx hy3-security-mcp` (no `--from` needed).

`--env` 可重复多次,每个 `KEY=VALUE` 一项;`--scope` 还可选 `local`(默认,仅本机可见)或 `user`(跨项目)。上面的命令把 `$HY3_API_KEY` 从你当前 shell 环境里取值写入 `.mcp.json`——**不要把真实密钥直接提交到仓库**,`.mcp.json` 若已加入版本控制,建议改用下面的 `${HY3_API_KEY}` 展开写法。

`--env` may be repeated per `KEY=VALUE`; `--scope` also accepts `local` (default, this machine only) or `user` (cross-project). The command above resolves `$HY3_API_KEY` from your current shell into `.mcp.json` at write time — **do not commit a real key**; if `.mcp.json` is version-controlled, prefer the `${HY3_API_KEY}` expansion form below instead.

## 方式二:直接写 `.mcp.json` / Option 2: hand-write `.mcp.json`

Claude Code 的 `.mcp.json` 支持 `${VAR}` 在 `env`/`command`/`args` 等字段里做环境变量展开(启动时从宿主 shell 环境取值),因此可以把下面这份配置**原样提交到仓库**而不含任何真实密钥——参见 [`examples/claude-code.mcp.json`](../../examples/claude-code.mcp.json):

Claude Code's `.mcp.json` supports `${VAR}` expansion in `env`/`command`/`args` (resolved from the host shell environment at launch), so the following can be **committed as-is** with no real secret inside — see [`examples/claude-code.mcp.json`](../../examples/claude-code.mcp.json):

```json
{
  "mcpServers": {
    "hy3-security-mcp": {
      "command": "uvx",
      "args": ["hy3-security-mcp"],
      "env": {
        "HY3_BASE_URL": "https://openrouter.ai/api/v1",
        "HY3_API_KEY": "${HY3_API_KEY}",
        "HY3_MODEL": "tencent/hy3:free"
      }
    }
  }
}
```

放到项目根目录的 `.mcp.json`,并确保运行 Claude Code 的 shell 里已 `export HY3_API_KEY=...`。

Place it at the project root as `.mcp.json`, and make sure `HY3_API_KEY` is exported in the shell that launches Claude Code.

## 验证连接 / Verify the connection

- `claude mcp list` — 列出已注册的 server 及其状态。
- 在 Claude Code 会话里输入 `/mcp` — 查看 MCP server 状态面板,应能看到 `hy3-security-mcp` 已连接,并列出 4 个工具:`audit_command`、`review_diff`、`scan_secrets`、`vuln_intel`。

`claude mcp list` lists registered servers and their status. Inside a Claude Code session, `/mcp` shows the MCP status panel — `hy3-security-mcp` should show as connected with all 4 tools listed.

## 端到端演示 / End-to-end demo

在 Claude Code 会话里让它调用 `audit_command` 审计一条明显危险的命令:

Ask Claude Code, in a session, to call `audit_command` on an obviously dangerous command:

> 请使用 audit_command 工具审计这条命令是否安全:`rm -rf /`
>
> Use the audit_command tool to check whether this command is safe: `rm -rf /`

预期结果(命中确定性快速路径,`source: "fast_path"`,不发生任何 LLM/网络调用):

Expected result (caught by the deterministic fast path, `source: "fast_path"`, no LLM/network call at all):

```json
{
  "level": "deny",
  "category": "destructive_fs",
  "rationale": "快速路径拦截:rm -rf 指向根目录/系统路径/家目录,递归删除不可逆",
  "safer_alternative": null,
  "source": "fast_path"
}
```
