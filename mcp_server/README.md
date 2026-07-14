# Hy3 Code Review MCP Server

Hy3 Code Review MCP Server 是一个基于 MCP Python SDK 的本地代码评审服务。它通过
stdio 与 Cursor、CodeBuddy 等 MCP 客户端通信，读取 Git diff 或调用方提供的 unified
diff，并调用 OpenAI 兼容的 Hy3 API 完成代码审查、变更解释、测试设计和 Pull Request
摘要生成。

服务采用只读设计：不会修改文件、执行测试、创建提交或推送代码。

## 功能与架构

```text
MCP Client
    │ stdio
    ▼
FastMCP Server
    │
    ├── GitService ── 读取并过滤 Git diff
    ├── ReviewService ── 组装任务和上下文
    └── Hy3Client ── 调用 OpenAI 兼容 Hy3 Chat Completions
```

核心实现包括：

- MCP Python SDK `FastMCP` stdio Server；
- 4 个只读、非破坏、幂等的代码评审工具；
- OpenAI 兼容 Hy3 异步客户端；
- working tree、staged、Git refs 和直接传入 diff 四种输入来源；
- 工作区路径限制、危险 Git ref 拒绝、敏感文件过滤和 diff 大小限制；
- MCP `isError=true` 结构化错误，包含错误码、修复建议和可重试标记；
- Cursor 与 CodeBuddy 项目级配置示例；
- 独立真实 API 冒烟命令和自动化测试。

## 目录结构

以下文件随仓库提供：

```text
mcp_server/
├── .env.example
├── .gitignore
├── README.md
├── pyproject.toml
├── examples/
│   ├── codebuddy.mcp.json
│   ├── cursor.mcp.json
│   └── demo-security-bug.diff
├── src/hy3_code_review_mcp/
│   ├── config.py
│   ├── git_service.py
│   ├── hy3_client.py
│   ├── prompts.py
│   ├── review_service.py
│   ├── server.py
│   ├── smoke_test.py
│   └── tool_errors.py
└── tests/
```

## MCP 工具

| 工具 | 功能 | 默认推理模式 |
|---|---|---|
| `review_git_diff` | 按正确性、安全性、性能和可维护性审查变更，输出证据、严重度、影响和修复建议 | `high` |
| `explain_code_changes` | 解释变更目的、行为影响、兼容性和潜在回归 | `low` |
| `suggest_test_cases` | 设计正常、边界、失败、回归和安全测试 | `high` |
| `generate_pr_summary` | 生成 PR 标题、变更摘要、风险和验证清单 | `no_think` |

所有工具都支持以下 diff 来源：

| `source` | 输入 |
|---|---|
| `working_tree` | 当前仓库未暂存改动 |
| `staged` | 当前仓库已暂存改动 |
| `refs` | `base_ref` 到工作区，或 `base_ref` 与 `target_ref` 之间的差异 |
| `provided` | `provided_diff` 中直接传入的 unified diff |

公共参数包括：

- `repository_path`：`HY3_WORKSPACE_ROOT` 内的 Git 仓库路径；
- `source`：diff 来源；
- `base_ref`、`target_ref`：`refs` 模式使用的 Git 引用；`base_ref` 必填，`target_ref` 可选；
- `provided_diff`：`provided` 模式必填的 diff 文本；
- `language`：返回语言，例如 `Chinese` 或 `English`。

工具专属参数包括：

- `review_git_diff.focus`：`all`、`correctness`、`security`、`performance` 或
  `maintainability`；
- `suggest_test_cases.test_framework`：可选测试框架，例如 `pytest` 或 `Vitest`。

## 运行要求

- Python 3.11 或更高版本；
- `uv`；
- Git；
- 可用的 OpenAI 兼容 Hy3 API，包括 Base URL、API Key 和模型名。

## 安装

以下命令适用于 macOS/Linux，并从仓库根目录执行。

创建项目虚拟环境并安装 Server：

```bash
uv venv mcp_server/.venv
uv pip install --python mcp_server/.venv/bin/python -e ./mcp_server
```

安装完成后会生成以下命令：

```text
mcp_server/.venv/bin/hy3-code-review-mcp
mcp_server/.venv/bin/hy3-code-review-smoke-test
```

确认 Server 入口可用：

```bash
mcp_server/.venv/bin/hy3-code-review-mcp --version
mcp_server/.venv/bin/hy3-code-review-mcp --help
```

直接运行不带参数的 `hy3-code-review-mcp` 会进入 stdio 协议循环，通常应由 MCP 客户端
启动，不应在普通交互式终端中长期运行。

## 配置 Hy3

复制配置模板：

```bash
cp mcp_server/.env.example mcp_server/.env
chmod 600 mcp_server/.env
```

编辑 `mcp_server/.env`：

```dotenv
HY3_API_KEY=replace-with-your-api-key
HY3_BASE_URL=https://tokenhub.tencentmaas.com/v1
HY3_MODEL=hy3
HY3_REASONING_EFFORT=high
HY3_TIMEOUT=120
HY3_MAX_DIFF_CHARS=120000
HY3_WORKSPACE_ROOT=/absolute/path/to/Hy3
```

`HY3_WORKSPACE_ROOT` 须替换为当前仓库或允许访问的工作区根目录的真实绝对路径。
`mcp_server/.env` 已被
`mcp_server/.gitignore` 忽略，不要把真实 API Key 硬编码入示例配置或客户端 JSON。

配置项说明：

| 环境变量 | 必需 | 默认值 | 说明 |
|---|---:|---|---|
| `HY3_ENV_FILE` | 否 | 无 | 显式 dotenv 路径；客户端配置使用此变量 |
| `HY3_API_KEY` | 是 | 无 | Hy3 API Key |
| `HY3_BASE_URL` | 是 | 无 | OpenAI 兼容 API Base URL |
| `HY3_MODEL` | 否 | `hy3` | 模型名 |
| `HY3_REASONING_EFFORT` | 否 | `high` | `high`、`low` 或 `no_think` |
| `HY3_TIMEOUT` | 否 | `120` | API 请求超时秒数 |
| `HY3_MAX_DIFF_CHARS` | 否 | `120000` | 单次 diff 最大字符数 |
| `HY3_WORKSPACE_ROOT` | 否 | Server 启动目录 | Server 可以访问的工作区根目录 |

验证配置但不调用 API：

```bash
HY3_ENV_FILE="$(pwd)/mcp_server/.env" \
  mcp_server/.venv/bin/hy3-code-review-mcp --check-config
```

## Hy3 冒烟验证

使用仓库提供的 `mcp_server/examples/demo-security-bug.diff` 发起一次真实代码审查：

```bash
HY3_ENV_FILE="$(pwd)/mcp_server/.env" \
  mcp_server/.venv/bin/hy3-code-review-smoke-test \
  --diff-file mcp_server/examples/demo-security-bug.diff
```

该命令会真实调用 Hy3。Demo diff 包含参数化 SQL 被替换为字符串拼接
以及日志记录个人信息的变更，可用于验证安全审查输出。

## 配置 Cursor

1. 确认已经完成“安装”和“配置 Hy3”。
2. 在仓库根目录创建 Cursor 项目配置：

```bash
mkdir -p .cursor
cp mcp_server/examples/cursor.mcp.json .cursor/mcp.json
```

3. 编辑 `.cursor/mcp.json`，将其中所有 `/absolute/path/to/Hy3` 替换为当前仓库根目录的
真实绝对路径。可以使用 `pwd` 查看该路径。

模板内容：

```json
{
  "mcpServers": {
    "hy3-code-review": {
      "command": "/absolute/path/to/Hy3/mcp_server/.venv/bin/hy3-code-review-mcp",
      "env": {
        "HY3_ENV_FILE": "/absolute/path/to/Hy3/mcp_server/.env",
        "HY3_WORKSPACE_ROOT": "/absolute/path/to/Hy3"
      }
    }
  }
}
```

重载 Cursor 后，在 MCP 设置中确认 `hy3-code-review` 已连接，并能看到 4 个工具。

## 配置 CodeBuddy

1. 确认已经完成“安装”和“配置 Hy3”。
2. 在仓库根目录复制项目级配置：

```bash
cp mcp_server/examples/codebuddy.mcp.json .mcp.json
```

3. 编辑 `.mcp.json`，将其中所有 `/absolute/path/to/Hy3` 替换为当前仓库根目录的真实
绝对路径。

模板内容：

```json
{
  "mcpServers": {
    "hy3-code-review": {
      "type": "stdio",
      "command": "/absolute/path/to/Hy3/mcp_server/.venv/bin/hy3-code-review-mcp",
      "env": {
        "HY3_ENV_FILE": "/absolute/path/to/Hy3/mcp_server/.env",
        "HY3_WORKSPACE_ROOT": "/absolute/path/to/Hy3"
      },
      "description": "Read-only Git diff review powered by Hy3"
    }
  }
}
```

如果已安装 CodeBuddy CLI，也可以直接添加项目级 Server：

```bash
PROJECT_ROOT="$(pwd)"
codebuddy mcp add-json --scope project hy3-code-review \
  "{\"type\":\"stdio\",\"command\":\"${PROJECT_ROOT}/mcp_server/.venv/bin/hy3-code-review-mcp\",\"env\":{\"HY3_ENV_FILE\":\"${PROJECT_ROOT}/mcp_server/.env\",\"HY3_WORKSPACE_ROOT\":\"${PROJECT_ROOT}\"},\"description\":\"Read-only Git diff review powered by Hy3\"}"
```

检查 CodeBuddy MCP 状态：

```bash
codebuddy mcp list
codebuddy mcp get hy3-code-review
```

## 调用示例

### 审查未暂存改动

在 Cursor 或 CodeBuddy Agent 中输入：

```text
请调用 hy3-code-review 的 review_git_diff 工具审查当前仓库未暂存的改动。
repository_path="."，source="working_tree"，focus="all"，language="Chinese"。
```

### 审查固定 Demo diff

```text
请读取 mcp_server/examples/demo-security-bug.diff 的完整内容，然后调用
hy3-code-review 的 review_git_diff 工具。
source="provided"，provided_diff 使用文件完整内容，focus="security"，
language="Chinese"。请给出证据、影响和修复建议。
```

### 生成测试建议

```text
请读取 mcp_server/examples/demo-security-bug.diff 的完整内容，然后调用
hy3-code-review 的 suggest_test_cases 工具。
source="provided"，provided_diff 使用文件完整内容，test_framework="pytest"，
language="Chinese"。缺陷测试必须以修复后的安全行为为通过条件。
```

### 解释代码变更

```text
请调用 hy3-code-review 的 explain_code_changes 工具解释当前未暂存改动。
repository_path="."，source="working_tree"，language="Chinese"。
```

### 生成 PR 摘要

```text
请调用 hy3-code-review 的 generate_pr_summary 工具总结当前已暂存改动。
repository_path="."，source="staged"，language="Chinese"。
```

## 错误返回

工具失败时返回 MCP `isError=true`，并在文本和 `structuredContent` 中提供相同的错误对象：

```json
{
  "ok": false,
  "error": {
    "code": "EMPTY_DIFF",
    "message": "the selected diff is empty",
    "suggested_action": "Choose a diff source that currently contains changes.",
    "retryable": false
  }
}
```

错误码覆盖配置错误、输入错误、工作区越界、无效仓库或 Git ref、空 diff、Git 超时、
Hy3 认证、限流、连接、请求超时和服务端错误。
