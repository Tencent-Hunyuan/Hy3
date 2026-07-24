# Cursor and CodeBuddy / Cursor 与 CodeBuddy

## English

### 1. Prerequisites

- Node.js 22 or newer must be visible on the client process `PATH`.
- Run commands from the Hy3 repository root unless a step says otherwise.
- Do not add a Hy3 key for the deterministic demo.

Prepare the server and verify the committed project configurations:

```bash
cd mcp_servers/mcp_quality_gate
npm ci
npm run verify:delivery
cd ../..
```

The verification command builds the package, validates `/.cursor/mcp.json` and
`/.mcp.json`, performs a real MCP stdio handshake, discovers exactly four tools,
and calls `mcpq_inspect_server` against `fixture-good`.

### 2. Cursor

Cursor reads `/.cursor/mcp.json` as a project configuration. Start Cursor Agent
from the repository root, approve the server, and inspect the exact public
argument surface:

```bash
agent login
agent mcp enable hy3-mcp-quality-gate
agent mcp list
agent mcp list-tools hy3-mcp-quality-gate
```

`agent login` uses Cursor's browser authentication flow. Complete it yourself;
never paste an account credential or API key into a project file or verification
record.

Expected evidence:

```text
hy3-mcp-quality-gate: ready
Tools for hy3-mcp-quality-gate (4):
- mcpq_audit_contracts (...)
- mcpq_compare_contracts (...)
- mcpq_generate_probe_suite (...)
- mcpq_inspect_server (...)
```

Use this bounded call in Cursor Agent:

```text
Call mcpq_inspect_server exactly once with target_id fixture-good and
include_schemas false. Report only the returned status and discovered tool names.
```

Expected result: `status=pass`, with `fixture_echo` and `fixture_sum`.

### 3. CodeBuddy

CodeBuddy reads `/.mcp.json` as project scope. Start it from the repository root:

```bash
codebuddy mcp list
codebuddy mcp get hy3-mcp-quality-gate
```

On first startup, CodeBuddy asks you to choose the Chinese, international,
enterprise, or Tencent-internal login flow and opens the corresponding browser
page. Complete authentication yourself; the project must not store the resulting
credential.

The first project connection requires explicit approval. In interactive
CodeBuddy, open `/mcp`, select `hy3-mcp-quality-gate`, inspect the command and
arguments, and approve only this server. A healthy connection reports:

```text
Scope: project
Status: Connected
Type: stdio
Command: node
```

Use the same bounded call:

```text
Call mcpq_inspect_server exactly once with target_id fixture-good and
include_schemas false. Report only the returned status and discovered tool names.
```

The CLI can also use an explicit configuration:

```bash
codebuddy --mcp-config .mcp.json --strict-mcp-config
```

### 4. More runnable calls

Deterministic audit, with no provider credential:

```text
Call mcpq_audit_contracts for target_id fixture-audit-bad with include_hy3 false.
Return status, overall score, and each rule_id with its evidence_path.
```

Compatibility comparison:

```text
Call mcpq_compare_contracts with baseline_target_id fixture-compat-baseline,
current_target_id fixture-compat-breaking, include_non_breaking true, and
include_hy3 false. Return status and the unique COMPAT rule IDs.
```

Probe generation needs a configured Hy3 endpoint. Generated probes are inert
records and are never executed by the quality gate.

### 5. Real target registry

Copy `examples/targets.example.json` to the ignored
`mcp_servers/mcp_quality_gate/targets.json`, edit only locally, then change
`MCPQ_TARGETS_FILE` in the project client configuration to that relative path.
Never put an API key, token, password, personal home path, or unrestricted shell
command in a committed configuration.

### 6. Troubleshooting

- `node: No such file or directory`: start the client from a shell where
  `node --version` succeeds, or install Node.js 22+.
- `needs approval`: inspect the exact project command and approve this server in
  the client MCP settings.
- server starts but the registry is empty: confirm `MCPQ_TARGETS_FILE` is relative
  to the repository root, or use an absolute local path only in an ignored private
  configuration.
- Hy3 audit is `partial`: this is expected when `include_hy3=true` but no usable
  endpoint credential is present; use `include_hy3=false` for offline checks.
- stdout protocol error: the target MCP Server must write diagnostics to stderr,
  never stdout.

## 中文

### 1. 前置条件

- 客户端进程的 `PATH` 中必须能找到 Node.js 22 或更新版本。
- 除非步骤另有说明，都从 Hy3 仓库根目录运行。
- 确定性演示不需要配置 Hy3 密钥。

先构建并验证已提交的项目配置：

```bash
cd mcp_servers/mcp_quality_gate
npm ci
npm run verify:delivery
cd ../..
```

该命令会检查 `/.cursor/mcp.json` 与 `/.mcp.json`，完成真实 stdio 握手，
发现 4 个工具，并调用 `fixture-good`。

### 2. Cursor

Cursor 把 `/.cursor/mcp.json` 作为项目级配置。从仓库根目录启动 Cursor
Agent，批准 Server，并检查公开参数：

```bash
agent login
agent mcp enable hy3-mcp-quality-gate
agent mcp list
agent mcp list-tools hy3-mcp-quality-gate
```

`agent login` 会打开 Cursor 的官方浏览器认证流程。请自行完成认证，不要把账号
凭据或 API key 写入项目文件或验证记录。

然后输入：

```text
只调用一次 mcpq_inspect_server，target_id 使用 fixture-good，
include_schemas 使用 false。只汇报 status 和发现的工具名。
```

预期为 `status=pass`，工具名是 `fixture_echo` 与 `fixture_sum`。

### 3. CodeBuddy

CodeBuddy 把 `/.mcp.json` 作为 project scope：

```bash
codebuddy mcp list
codebuddy mcp get hy3-mcp-quality-gate
```

首次启动时，CodeBuddy 会让用户选择中国站、国际站、企业域或腾讯内部登录，并
打开对应浏览器页面。请自行完成认证，项目中不得保存认证结果。

第一次连接需要显式批准。在交互式 CodeBuddy 中打开 `/mcp`，检查命令与参数后，
只批准 `hy3-mcp-quality-gate`。健康连接会显示 project、Connected、stdio。
随后使用与 Cursor 相同的受限调用文本。

也可以显式指定配置：

```bash
codebuddy --mcp-config .mcp.json --strict-mcp-config
```

### 4. 更多调用

离线确定性审计：

```text
调用 mcpq_audit_contracts，target_id 使用 fixture-audit-bad，
include_hy3 使用 false。返回 status、overall 分数以及每个 rule_id 和
evidence_path。
```

兼容性比较：

```text
调用 mcpq_compare_contracts，baseline_target_id 使用
fixture-compat-baseline，current_target_id 使用 fixture-compat-breaking，
include_non_breaking 使用 true，include_hy3 使用 false。
返回 status 和唯一的 COMPAT 规则 ID。
```

生成探针需要配置 Hy3。探针只是不会被质量门禁自动执行的数据记录。

### 5. 真实目标与排错

把 `examples/targets.example.json` 复制为已忽略的本地 `targets.json`，只在
本机修改，再把客户端配置中的 `MCPQ_TARGETS_FILE` 改为对应相对路径。不要把
密钥、token、密码、个人主目录路径或不受限制的 shell 命令提交进仓库。

- `node: No such file or directory`：从 `node --version` 成功的 shell 启动
  客户端，或安装 Node.js 22+。
- `needs approval`：核对项目命令后在 MCP 设置中批准该 Server。
- 注册表为空：确认路径相对仓库根目录。
- Hy3 审计为 `partial`：未配置端点时属于预期；离线检查使用
  `include_hy3=false`。
- stdout 协议错误：目标 MCP Server 的诊断必须写 stderr。
