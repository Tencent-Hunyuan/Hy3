# Hy3 CI Copilot

简体中文 | [English](README.md)

Hy3 CI Copilot 是一个本地 stdio MCP Server。它读取 CI 日志、工作流和受限的仓库上下文，
调用 Hy3 输出有证据的故障根因、回归对比、工作流审查和可执行修复计划。

> **数据提示：** 被选中的日志、工作流、构建清单和 Git 元数据会发送到 `HY3_BASE_URL`
> 指定的服务。Server 会尽力脱敏常见凭据，但使用前仍应主动移除敏感数据。Server 不执行
> 模型建议，也不修改仓库文件。

## MCP Tools

| Tool | 功能 | 必填参数 |
| --- | --- | --- |
| `diagnose_ci_failure` | 根据失败日志与仓库上下文定位根因并给出置信度 | `log_path` |
| `compare_ci_runs` | 对比成功与失败运行，隔离回归变化 | `failed_log_path`、`successful_log_path` |
| `review_ci_workflow` | 审查 CI YAML 的正确性、可复现性和易失败配置 | `workflow_path` |
| `build_ci_fix_plan` | 把诊断转换为按文件拆分的修改、验证与回滚计划 | `diagnosis` |

所有工具的参数说明、默认值和枚举都会通过 MCP `tools/list` 暴露；核心分析均实际调用 Hy3。

## Demo 与客户端实测

![CodeBuddy 调用 Hy3 CI Copilot](docs/demo.gif)

[客户端实测记录](docs/client-validation.md)列出了 CodeBuddy CN 1.106.1 与 Claude Code
2.1.153 的精确调用参数、Hy3 实际解析模型和返回结果。

## 环境要求

- Python 3.10+
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/)
- 自部署或 OpenRouter 上的 OpenAI-compatible Hy3 endpoint

## 一键运行

在本目录执行：

```bash
export HY3_API_KEY=EMPTY
export HY3_BASE_URL=http://127.0.0.1:8000/v1
export HY3_MODEL=hy3
export HY3_ALLOWED_ROOTS=/仓库的绝对路径

uvx --from . hy3-ci-copilot
```

命令启动后会在 stdio 上等待 MCP JSON-RPC。使用 OpenRouter 时改为：

```bash
export HY3_API_KEY='你的 OpenRouter Key'
export HY3_BASE_URL=https://openrouter.ai/api/v1
export HY3_MODEL=tencent/hy3
```

API Key 只能通过环境变量传入，不能作为 tool 参数，也不会由 Server 保存。无鉴权的本地服务
也应显式设置 `HY3_API_KEY=EMPTY`。

MCP 客户端使用仓库内配置前，先创建只保存在本机的环境文件：

```bash
umask 077
cp .env.example .env
# 在 .env 中设置 HY3_API_KEY、HY3_BASE_URL、HY3_MODEL 和 HY3_ALLOWED_ROOTS。
```

`.env` 已被 Git 忽略。项目配置通过 `uv run --env-file` 加载，跨仓库示例通过
`uvx --env-file` 加载，因此不依赖已运行客户端进程是否继承当前 shell 的 Key。

长期安装：

```bash
uv tool install .
hy3-ci-copilot
```

协议冒烟测试：

```bash
uv run --extra dev python scripts/stdio_smoke.py
```

该脚本通过官方 MCP Python Client 初始化真实 stdio 会话并检查 4 个 tool，不调用 Hy3 API。

## 环境变量

| 变量 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `HY3_API_KEY` | 是 | 无 | Endpoint Key；本地无鉴权服务填写 `EMPTY` |
| `HY3_BASE_URL` | 否 | `http://127.0.0.1:8000/v1` | OpenAI-compatible Base URL |
| `HY3_MODEL` | 否 | `hy3` | Hy3 模型 ID |
| `HY3_API_STYLE` | 否 | `auto` | `native`、`openrouter` 或自动判断 |
| `HY3_ALLOWED_ROOTS` | 否 | Server 工作目录 | Unix 用 `:`、Windows 用 `;` 分隔多个根目录 |
| `HY3_TIMEOUT_SECONDS` | 否 | `120` | API 超时，范围 1-600 秒 |
| `HY3_MAX_INPUT_CHARS` | 否 | `120000` | 输入总字符预算 |
| `HY3_MAX_OUTPUT_TOKENS` | 否 | `4096` | 最大输出 token 数 |
| `HY3_MAX_RETRIES` | 否 | `2` | HTTP 429 和临时 5xx 的重试次数 |

自部署接口使用 `chat_template_kwargs.reasoning_effort`；OpenRouter 使用
`reasoning.effort`。MCP 参数支持 Hy3 官方的 `no_think`、`low`、`high`。

## CodeBuddy 配置与调用

CodeBuddy CN 从工作区根目录的 `.mcp.json` 读取项目级 MCP 配置。本包已提供可用的
[`.mcp.json`](.mcp.json)，直接把本包目录作为工作区即可。接入其他仓库时，将
[`examples/clients/codebuddy.mcp.json`](examples/clients/codebuddy.mcp.json) 复制到仓库根目录并
命名为 `.mcp.json`。将 `/ABSOLUTE/PATH/TO/PACKAGE` 替换为本包路径，将
`/ABSOLUTE/PATH/TO/TARGET_REPOSITORY` 替换为允许 CodeBuddy 读取的目标仓库。

CodeBuddy 不会展开 MCP 配置里的 `${env:VAR}`，因此项目配置通过 `uv run --frozen` 读取
已忽略的 `.env`，Key 不会出现在 MCP JSON 中；跨仓库配置则使用 `uvx --env-file`。准备
`.env` 后启动新 CodeBuddy 进程，让项目 Server 被重新发现。macOS 默认安装路径下可直接运行：

```bash
cd /absolute/path/to/Hy3/mcp_servers/hy3_ci_copilot
'/Applications/CodeBuddy CN.app/Contents/Resources/app/bin/code' chat \
  -m agent --maximize \
  '必须调用 hy3-ci-copilot 的 diagnose_ci_failure；log_path 使用 logs/failed.log，repository_path 使用 examples/demo_repository，output_language 使用 zh-CN，reasoning_effort 使用 low。只返回首要根因和一条验证命令，不要修改文件。'
```

普通 `chat` 会把当前目录作为工作区；不要使用 `-n`，`-r` 可能复用其他工作区窗口。
CodeBuddy 的 `--add-mcp` 写入另一套编辑器级配置，因此本 demo 以项目 `.mcp.json` 为准。
配置中的 `timeout` 单位是毫秒，已设为 `180000`（3 分钟）。`HY3_TIMEOUT_SECONDS` 应不高于
该客户端时限；当上游 `high` 推理延迟不稳定时，客户端 demo 建议使用 `low`。

## Claude Code 配置与调用

Claude Code 可以直接加载项目 [`.mcp.json`](.mcp.json)，无需修改用户级 MCP 设置。准备好
`.env` 后，在本包目录执行：

```bash
claude -p \
  --mcp-config .mcp.json \
  --strict-mcp-config \
  --allowedTools 'mcp__hy3-ci-copilot__diagnose_ci_failure' \
  --verbose \
  --output-format stream-json \
  '必须调用 hy3-ci-copilot 的 diagnose_ci_failure；log_path 使用 logs/failed.log，repository_path 使用 examples/demo_repository，output_language 使用 en，reasoning_effort 使用 high。返回首要根因和一条验证命令，不要修改文件。'
```

[`examples/clients/claude-code.mcp.json`](examples/clients/claude-code.mcp.json) 是跨仓库配置，
使用前需替换其中的包路径和目标仓库路径占位符。

## Cline 配置

[`examples/clients/cline_mcp_settings.json`](examples/clients/cline_mcp_settings.json) 给出了配置
格式。Cline CLI 可直接添加，其中绝对路径会在写入前由 shell 展开：

```bash
PACKAGE_DIR="$(pwd)"
cline mcp add hy3-ci-copilot --yes -- \
  uvx --env-file "$PACKAGE_DIR/.env" --from "$PACKAGE_DIR" hy3-ci-copilot
```

用 `cline config mcp --json` 检查注册结果。Cline CLI 3.0.39 默认使用全局 MCP 设置。隔离验证
前应先停止已有 Cline hub，再在注册和启动时都设置
`CLINE_MCP_SETTINGS_PATH=/path/to/settings.json`，确保新 hub 使用隔离的设置文件。该版本还把
单次 MCP 请求超时固定为 5 秒，短于 Hy3 的常见响应时间，因此这里只提供配置示例，不作为
客户端实调证据；双客户端实测使用 CodeBuddy 与 Claude Code。

## 可复现示例

[`examples/demo_repository`](examples/demo_repository) 包含 Python 3.11 成功日志、Python 3.12
失败日志和对应 workflow。调用 `compare_ci_runs`：

```text
failed_log_path: logs/failed.log
successful_log_path: logs/successful.log
repository_path: /absolute/path/to/examples/demo_repository
output_language: zh-CN
reasoning_effort: high
```

有效结果应引用 Python 版本变化和 `distutils` 缺失；模型措辞可能不同，但忽略输入证据的结果
不能记为验证通过。

## 安全边界

- `HY3_ALLOWED_ROOTS` 是唯一允许根；tool 不能越界读取。
- 拒绝 symlink 逃逸、`.git` 内容、空文件和二进制文件；workflow YAML 受 alias 数量、事件数量和
  嵌套深度上限约束。
- 发送前移除 ANSI/控制符、显式标记截断，并脱敏常见 Key、Token、密码、鉴权头、URL 凭据
  和私钥。
- Git 上下文只执行固定 argv、5 秒超时的只读命令，不经过 shell，也不执行模型生成的命令。
- 4 个 tool 都无状态、只读；输出只是分析文本，不会自动修改文件。

## 开发与验证

```bash
uv sync --extra dev
uv run --extra dev pytest
uv run --extra dev ruff check src tests scripts
uv build
```

测试会启动真实 stdio MCP 子进程，并通过本地 fake Chat Completions Server 断言 4 个 tool
均调用配置的 Hy3-compatible endpoint。

## License

Apache-2.0，与 Hy3 主仓库一致。
