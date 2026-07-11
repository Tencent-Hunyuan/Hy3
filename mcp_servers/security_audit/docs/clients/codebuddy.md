# 在 CodeBuddy 中使用 / Using hy3-security-mcp in CodeBuddy

> 本文档基于 CodeBuddy 官方 CLI 文档([codebuddy.ai/docs/cli/mcp](https://www.codebuddy.ai/docs/cli/mcp))撰写。如果你使用的是内部/企业版本(命名或行为略有差异,有时称作 WorkBuddy),其 `.mcp.json` 结构应与下方一致——这是通用的 MCP stdio server 配置形状(`command`/`args`/`env`);如有出入,以你所用版本自带的帮助文档为准,不要假设本文列出的 CLI 参数在所有版本上都可用。
>
> This doc is based on CodeBuddy's public CLI docs ([codebuddy.ai/docs/cli/mcp](https://www.codebuddy.ai/docs/cli/mcp)). If you're on an internal/enterprise build (sometimes referred to as WorkBuddy) that differs, the `.mcp.json` shape below should still hold — it's the generic MCP stdio config shape (`command`/`args`/`env`). If your build's CLI differs, defer to its own `--help` output rather than assuming every flag below is present.

## 前置条件 / Prerequisites

- Python ≥ 3.11,以及 `uv`/`uvx`(或 `pip install .` 到某个环境)。
- 一个 Hy3 API key(见仓库根目录 [`.env.example`](../../.env.example) 的三种后端选项)。
- CodeBuddy CLI(`codebuddy`)或支持 MCP 的 CodeBuddy IDE。

Python ≥ 3.11, plus `uv`/`uvx` (or `pip install .` into some environment). A Hy3 API key (see the repo root [`.env.example`](../../.env.example)). The CodeBuddy CLI (`codebuddy`) or a CodeBuddy IDE build with MCP support.

## 方式一:项目级 `.mcp.json`(推荐)/ Option 1: project-level `.mcp.json` (recommended)

CodeBuddy 的 MCP 配置与 Claude Code/Cursor 是同一套通用格式:顶层 `mcpServers`,每个 server 一个 `type`/`command`/`args`/`env`。项目级配置文件路径为仓库根目录的 `.mcp.json`(用户级为 `~/.codebuddy/.mcp.json`)。内容同 [`examples/codebuddy.mcp.json`](../../examples/codebuddy.mcp.json):

CodeBuddy uses the same generic MCP config shape as Claude Code/Cursor: top-level `mcpServers`, each server a `type`/`command`/`args`/`env` block. The project-level file is `.mcp.json` at the repo root (user-level: `~/.codebuddy/.mcp.json`). Content matches [`examples/codebuddy.mcp.json`](../../examples/codebuddy.mcp.json):

```json
{
  "mcpServers": {
    "hy3-security-mcp": {
      "type": "stdio",
      "command": "uvx",
      "args": ["hy3-security-mcp"],
      "env": {
        "HY3_BASE_URL": "https://openrouter.ai/api/v1",
        "HY3_API_KEY": "REPLACE_WITH_YOUR_HY3_API_KEY",
        "HY3_MODEL": "tencent/hy3:free"
      }
    }
  }
}
```

**关于密钥占位符 / About the key placeholder**:CodeBuddy 官方文档未明确说明 `.mcp.json` 的 `env` 字段是否支持 `${VAR}` 从宿主环境展开(不同于 Claude Code/Cursor,二者的文档都明确写了这个能力)。为安全起见,**不要把真实密钥提交到版本控制**——本地把 `REPLACE_WITH_YOUR_HY3_API_KEY` 换成真实值,并确保 `.mcp.json` 不进 git(或加进 `.gitignore`),或改用下面的 CLI 方式,让密钥只落在本机配置里。

CodeBuddy's public docs don't explicitly confirm whether `.mcp.json`'s `env` field supports `${VAR}` host-environment expansion (unlike Claude Code/Cursor, whose docs state this explicitly). To be safe, **do not commit a real key** — substitute `REPLACE_WITH_YOUR_HY3_API_KEY` locally and keep `.mcp.json` out of git (or gitignore it), or use the CLI option below so the secret only lives in your local config.

## 方式二:CLI 添加(如果支持)/ Option 2: CLI add (if supported)

```bash
codebuddy mcp add-json --scope project hy3-security-mcp \
  '{"type":"stdio","command":"uvx","args":["hy3-security-mcp"],"env":{"HY3_BASE_URL":"https://openrouter.ai/api/v1","HY3_API_KEY":"'"$HY3_API_KEY"'","HY3_MODEL":"tencent/hy3:free"}}'
```

`codebuddy mcp add-json` 和 `codebuddy mcp add --scope user|project <name> -- <command> <args...>` 都记录在官方 CLI 文档中;但该文档没有给出 `mcp add` 传递 env 变量的专用 flag(不同于 Claude Code 的 `--env`),env 只在 `add-json` 的内联 JSON 里出现——因此这里用 `add-json`,而不是猜测一个可能不存在的 `--env` flag。

Both `codebuddy mcp add-json` and `codebuddy mcp add --scope user|project <name> -- <command> <args...>` are documented in the official CLI docs; the docs don't show a dedicated env-var flag for plain `mcp add` (unlike Claude Code's `--env`) — env only appears in `add-json`'s inline JSON — so this uses `add-json` rather than guessing at an `--env` flag that may not exist.

尚未发布到 PyPI 时,把 `"args":["hy3-security-mcp"]` 换成本地检出路径:`"args":["--from","/absolute/path/to/hy3-security-mcp","hy3-security-mcp"]`。

Until published to PyPI, replace `"args":["hy3-security-mcp"]` with a local-checkout form: `"args":["--from","/absolute/path/to/hy3-security-mcp","hy3-security-mcp"]`.

## 验证连接 / Verify the connection

- `codebuddy mcp list` — 列出已注册的 server 及状态(若你的版本支持)。
- 在 CodeBuddy IDE 里打开 Settings → MCP 面板,`hy3-security-mcp` 应显示为已连接,并列出 4 个工具:`audit_command`、`review_diff`、`scan_secrets`、`vuln_intel`。

`codebuddy mcp list` lists registered servers and status (if your build supports it). In the CodeBuddy IDE, open Settings → MCP; `hy3-security-mcp` should show as connected with all 4 tools listed.

## 端到端演示 / End-to-end demo

在 CodeBuddy 的对话/Agent 界面里输入:

In CodeBuddy's chat/agent interface:

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
