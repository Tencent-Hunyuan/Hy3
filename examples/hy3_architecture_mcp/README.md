# Hy3 Architecture MCP Server

A stdio [Model Context Protocol](https://modelcontextprotocol.io/) server that wraps the
**Hy3** large language model as a **technical-proposal review workflow**. Any MCP-compatible
client (CodeBuddy / WorkBuddy / Cursor / Cline / Claude Desktop …) can plug it in and drive an
end-to-end pipeline from a fuzzy requirement to an executable implementation plan.

```
模糊需求 ──▶ clarify_requirements ──▶ generate_technical_proposal
                                                        │
                                                        ▼
        create_implementation_plan ◀── review_technical_proposal
                        │
                        ▼
                  可执行实施计划

        analyze_project_context  ◀── 把可信本地文件喂入上述任一环节
```

Four tools call the Hy3 API (OpenAI-compatible) for reasoning; one tool reads trusted local
files inside a strict sandbox and feeds them as context. **No file is ever executed**, and no
path may escape `HY3_WORKSPACE_ROOT`.

---

## 目录

- [典型工作流](#典型工作流)
- [架构](#架构)
- [五个 Tool](#五个-tool)
- [环境要求](#环境要求)
- [安装](#安装)
- [环境变量](#环境变量)
- [启动](#启动)
- [客户端配置](#客户端配置)
- [端到端 Demo](#端到端-demo)
- [文件读取的安全边界](#文件读取的安全边界)
- [常见错误排查](#常见错误排查)
- [测试和开发](#测试和开发)
- [Demo 视频 / GIF](#demo-视频--gif)
- [License](#license)

---

## 典型工作流

1. **`clarify_requirements`** — 把一句模糊需求拆成「理解的目标 / 歧义 / 缺失信息 / 澄清问题 /
   验收标准 / 假设」。
2. 人工或上游 agent 回答澄清问题，补充用户规模、权限、数据量、成本等约束。
3. **`generate_technical_proposal`** — 基于澄清后的需求产出可评审方案（架构、技术选型、
   非功能设计、风险、开放问题）。
4. **`review_technical_proposal`** — 跨 8 个工程维度评审方案，给出 verdict / 0–100 分 / findings /
   优先动作。
5. **`create_implementation_plan`** — 把通过评审的方案拆成里程碑、任务、关键路径、可并行项与 DoD。
6. 任意环节可用 **`analyze_project_context`** 读取工作区内的可信文件（README、配置、源码）作为上下文，
   让 Hy3 的分析贴合你的真实仓库。

---

## 架构

```
┌──────────────────────────────────────────────────────────────────┐
│  MCP Client (CodeBuddy / Cursor / Cline / Claude Desktop ...)    │
│                      stdio JSON-RPC                             │
└───────────────────────────────┬──────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────┐
│                Hy3 Architecture MCP Server                       │
│  (FastMCP, mcp Python SDK, stdio transport)                      │
│                                                                  │
│   clarify_requirements      generate_technical_proposal          │
│   review_technical_proposal create_implementation_plan            │
│   analyze_project_context  ◀── 本地文件沙箱 (workspace-bound)     │
└───────┬──────────────────────────────────────────┬───────────────┘
        │ httpx[http2], 重试/超时/脱敏              │ pathlib, 沙箱
┌───────▼──────────────────┐          ┌────────────▼───────────────┐
│   Hy3 API (OpenAI 兼容)  │          │  HY3_WORKSPACE_ROOT 内文件 │
│   vLLM / SGLang :8000    │          │  (.md/.py/.ts/.json/...)    │
└──────────────────────────┘          └────────────────────────────┘
```

关键设计：

- **`hy3_client.Hy3Client`** — 单例异步客户端，封装认证、超时、指数退避重试（429/5xx）、
  结构化输出提取与 Pydantic 校验（失败时按方案六做一次修复重试）。API Key 仅用
  `Authorization: Bearer`，日志中一律脱敏。
- **`config.Settings`** — Pydantic Settings，全部参数从 `HY3_*` 环境变量读取并校验。
- **`tools.project_context`** — 唯一访问本地文件的工具，工作区边界 / 扩展名白名单 /
  敏感文件黑名单 / 大小限制 / 符号链接逃逸检查五重防护（见[安全边界](#文件读取的安全边界)）。
- **错误层** — `exceptions.py` 定义分层异常，工具把 `Hy3McpError` 转成 `RuntimeError`
  以便 MCP 传输层序列化。

---

## 五个 Tool

| # | Tool | 调用 Hy3 | 作用 |
|---|------|:---:|------|
| 1 | `clarify_requirements` | ✅ | 拆解模糊需求，输出澄清问题与验收标准 |
| 2 | `generate_technical_proposal` | ✅ | 生成可评审的技术方案 |
| 3 | `review_technical_proposal` | ✅ | 多维度评审方案并打分 |
| 4 | `create_implementation_plan` | ✅ | 把方案拆成里程碑与实施计划 |
| 5 | `analyze_project_context` | ✅ | 读取工作区内可信本地文件并结构化分析 |

> 四个核心 Tool 的推理全部由 Hy3 完成；`analyze_project_context` 先在本地沙箱里读取文件，
> 再把内容交给 Hy3 分析，文件本身**绝不被执行**。

### 1. `clarify_requirements`

**输入**

| 参数 | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `requirement` | string | ✅ | 原始模糊需求（非空） |
| `project_context` | string | – | 可选项目背景 |
| `constraints` | string[] | – | 已知约束 |
| `output_language` | string | – | 默认 `zh-CN` |
| `max_questions` | int | – | 澄清问题上限 1–20，默认 8 |

**输出**：`understood_goals` / `ambiguities` / `missing_information` /
`clarifying_questions` / `acceptance_criteria` / `assumptions`（均为 string[]）。

```jsonc
// 调用
{
  "requirement": "为一个 30 人研发团队构建内部知识库，支持 Markdown 和 PDF",
  "max_questions": 5
}
```

### 2. `generate_technical_proposal`

**输入**：`requirements`(必填) / `project_context` / `preferred_stack`[] / `constraints`[] /
`proposal_depth`(`brief`|`standard`|`detailed`) / `output_language`。

**输出**：`title` / `executive_overview` / `architecture{components,data_flow,interfaces}` /
`technology_choices[{name,rationale}]` / `alternatives[{name,description,tradeoffs}]` /
`non_functional_design{performance,reliability,observability,maintainability}` /
`risks[{description,severity,mitigation}]` / `open_questions`。

### 3. `review_technical_proposal`

**输入**：`proposal`(必填，方案文本) / `requirements`(原始需求，用于覆盖度) /
`review_dimensions`[](默认 8 维度) / `risk_threshold`(`low`|`medium`|`high`) / `output_language`。

默认评审维度：`requirement_coverage` / `maintainability` / `scalability` / `reliability` /
`cost` / `testability` / `observability` / `data_privacy`。

**输出**：`verdict`(`approve`|`approve_with_changes`|`reject`) / `score`(0–100) /
`strengths` / `findings[{id,severity,dimension,evidence,impact,recommendation}]` /
`missing_decisions` / `priority_actions`。

### 4. `create_implementation_plan`

**输入**：`proposal`(必填，已评审方案) / `team_size`(≥1) / `target_days`(≥1) /
`available_roles`[] / `output_language`。

**输出**：`milestones[{name,goal,tasks[{id,title,description,dependencies,suggested_role,
estimated_effort,deliverables,acceptance_criteria}]}]` / `critical_path` /
`parallelizable_work` / `delivery_risks` / `definition_of_done`。

### 5. `analyze_project_context`

**输入**：`paths`[](必填，文件或目录，相对工作区或工作区内绝对路径) / `include_content_summary`(bool) /
`max_depth`(0–10) / `output_language`。

**输出**：`detected_stack` / `project_structure` / `important_files` / `constraints` /
`architecture_observations` / `warnings`。

> Tool 的完整 JSON Schema 可由 MCP 客户端通过 `tools/list` 自动获取，参数约束
> （`max_questions` 1–20、`team_size`≥1、`max_depth` 0–10、`score` 0–100 等）均对外可见。

---

## 环境要求

- **Python ≥ 3.10**
- 一个可访问的 **Hy3** 部署（vLLM / SGLang，OpenAI 兼容接口）。参考仓库根目录的
  [README_CN.md](../../README_CN.md) 启动 vLLM：

  ```bash
  vllm serve tencent/Hy3 --tensor-parallel-size 8 --port 8000 --served-model-name hy3 \
    --tool-call-parser hy_v3 --reasoning-parser hy_v3 --enable-auto-tool-choice
  ```

---

## 安装

### 从源码安装（推荐，开发可用可编辑模式）

```bash
cd examples/hy3_architecture_mcp
pip install -e . --index-url https://pypi.org/simple/
```

安装后会注册控制台命令 `hy3-architecture-mcp`。

### 直接安装（已发布时）

```bash
pip install hy3-architecture-mcp
```

---

## 环境变量

所有变量带默认值，除 `HY3_WORKSPACE_ROOT` 外均可在不配置时运行（仅 `analyze_project_context`
需要它）。完整模板见 [`.env.example`](.env.example)。

| 变量 | 默认 | 说明 |
|---|---|---|
| `HY3_API_KEY` | `EMPTY` | Hy3 API Key。本地 vLLM/SGLang 可填任意值；**不得硬编码进代码或配置文件** |
| `HY3_BASE_URL` | `http://127.0.0.1:8000/v1` | OpenAI 兼容 base URL，需带 `/v1` |
| `HY3_MODEL` | `hy3` | 与部署的 `--served-model-name` 一致 |
| `HY3_REASONING_EFFORT` | `high` | `no_think` / `low` / `high`，默认 `high` 以适合方案/评审/计划 |
| `HY3_TIMEOUT_SECONDS` | `60` | 单次请求超时，范围 (0, 600] |
| `HY3_MAX_RETRIES` | `2` | 429/5xx 重试次数，范围 [0, 10] |
| `HY3_WORKSPACE_ROOT` | *(空)* | **`analyze_project_context` 必填**，文件读取的绝对根边界 |
| `HY3_MAX_FILE_SIZE_BYTES` | `1048576` | 单文件大小上限 |
| `HY3_MAX_TOTAL_SIZE_BYTES` | `5242880` | 单次调用总读取大小上限 |

---

## 启动

两种等价方式：

```bash
# 1) 控制台命令（pip install 后可用）
hy3-architecture-mcp

# 2) 模块方式
python -m hy3_architecture_mcp
```

服务通过 **stdio** 收发 JSON-RPC，不需要公网端口。客户端负责拉起进程。

快速自检（不开 Hy3，仅验证 stdio 与 Tool 发现）：

```bash
python examples/hy3_architecture_mcp/scripts/probe_stdio.py
# 期望输出：
#   initialize OK: hy3-architecture v1.28.1
#   TOOLS VIA STDIO (5): ['clarify_requirements', ...]
#   ALL 5 EXPECTED TOOLS PRESENT
```

---

## 客户端配置

> 下列配置按各客户端实际格式编写。`<ABSOLUTE_PROJECT_PATH>` 替换为你的项目绝对路径，
> `<YOUR_API_KEY>` 替换为你的 Key。**不要把真实密钥提交进仓库**——
> 建议通过系统环境变量或客户端的安全 secret 管理注入。

### CodeBuddy / WorkBuddy（项目级 `.mcp.json`）

在项目根目录放置 `.mcp.json`（CodeBuddy 与 WorkBuddy 均支持此项目级约定）：

```jsonc
{
  "mcpServers": {
    "hy3-architecture": {
      "command": "hy3-architecture-mcp",
      "args": [],
      "env": {
        "HY3_API_KEY": "<YOUR_API_KEY>",
        "HY3_BASE_URL": "http://127.0.0.1:8000/v1",
        "HY3_MODEL": "hy3",
        "HY3_REASONING_EFFORT": "high",
        "HY3_WORKSPACE_ROOT": "<ABSOLUTE_PROJECT_PATH>"
      }
    }
  }
}
```

如客户端不支持环境变量插值，请改用系统环境变量（Windows 用 `setx`，Linux/macOS 写入
`~/.bashrc` / `~/.zshrc`），配置文件中只保留 `command` 与 `args`：

```bash
# Linux / macOS
export HY3_API_KEY=... HY3_BASE_URL=http://127.0.0.1:8000/v1 HY3_MODEL=hy3 \
       HY3_WORKSPACE_ROOT=/abs/path/to/project
# Windows (PowerShell)
[Environment]::SetEnvironmentVariable("HY3_API_KEY","...","User")
[Environment]::SetEnvironmentVariable("HY3_WORKSPACE_ROOT","D:\path\to\project","User")
```

CLI 等价添加方式（以 CodeBuddy 为例）：

```bash
codebuddy mcp add hy3-architecture -- hy3-architecture-mcp
# 环境变量通过系统环境或 .mcp.json 的 env 字段提供
```

### Cursor

`Settings → MCP → Add new MCP Server`，或编辑 `~/.cursor/mcp.json`（用户级）/
项目内 `.cursor/mcp.json`（项目级）：

```jsonc
{
  "mcpServers": {
    "hy3-architecture": {
      "command": "hy3-architecture-mcp",
      "env": {
        "HY3_API_KEY": "<YOUR_API_KEY>",
        "HY3_BASE_URL": "http://127.0.0.1:8000/v1",
        "HY3_MODEL": "hy3",
        "HY3_WORKSPACE_ROOT": "<ABSOLUTE_PROJECT_PATH>"
      }
    }
  }
}
```

### Cline (`cline_mcp_settings.json`)

```jsonc
{
  "mcpServers": {
    "hy3-architecture": {
      "command": "hy3-architecture-mcp",
      "args": [],
      "env": {
        "HY3_API_KEY": "<YOUR_API_KEY>",
        "HY3_BASE_URL": "http://127.0.0.1:8000/v1",
        "HY3_MODEL": "hy3",
        "HY3_WORKSPACE_ROOT": "<ABSOLUTE_PROJECT_PATH>"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

> Windows 上若 `hy3-architecture-mcp` 不在 PATH，可改用
> `"command": "python", "args": ["-m", "hy3_architecture_mcp"]`。

---

## 端到端 Demo

示例需求（取自开发计划）：

> 「为一个 30 人研发团队构建内部知识库，支持 Markdown 和 PDF，回答必须附带来源引用，
> 文档每天更新，部署成本有限。」

`examples/demo_workflow.py` 用 MCP 客户端 SDK 依次驱动四个核心 Tool 跑完整流水线：

```bash
# 方式 A：连真实 Hy3 部署（需先启动 vLLM/SGLang）
export HY3_BASE_URL=http://127.0.0.1:8000/v1
export HY3_API_KEY=EMPTY
export HY3_WORKSPACE_ROOT=/abs/path/to/your/project
python examples/demo_workflow.py

# 方式 B：内置 mock 端点，无需 Hy3 即可演示流水线与 Tool 返回结构
python examples/demo_workflow.py --mock
```

Demo 会打印每一步的结构化输出（澄清问题 → 方案 → 评审 → 实施计划），并隐藏 API Key
与敏感路径。详见脚本内注释。

---

## 文件读取的安全边界

`analyze_project_context` 是唯一访问本地文件的工具，采用五重防护：

1. **工作区根边界** — 所有路径最终都要 `resolve()` 后落在 `HY3_WORKSPACE_ROOT` 之内，
   否则抛 `WorkspaceAccessError`。`HY3_WORKSPACE_ROOT` 未设置时直接拒绝运行。
2. **扩展名白名单** — 仅 `.md/.txt/.json/.toml/.yaml/.yml/.py/.js/.ts/.tsx/.jsx/.java/.go/.rs`
   等文本/代码文件可读。
3. **敏感文件黑名单** — `.env` 及其变体（`.env.local`/`.env.production`…）、`id_rsa`、
   `*.pem`/`*.key`/`*.crt`/`*.p12`/`*.keystore`、`credentials`、`.npmrc`/`.pypirc`/`.netrc`
   等一律拒绝，即使被直接显式指定。
4. **大小限制** — 单文件超 `HY3_MAX_FILE_SIZE_BYTES`、累计超 `HY3_MAX_TOTAL_SIZE_BYTES`
   均抛 `FileTooLargeError`；二进制文件（含 NUL 字节）与非 UTF-8 文件跳过并告警。
5. **符号链接逃逸检查** — 目录遍历时对每个文件再次 `resolve()` 校验，防止符号链接
   指向工作区外；同时剪除 `.git`/`node_modules`/`dist`/`.venv` 等目录。

此外 `HY3_API_KEY` 在所有日志中脱敏（`mask()`），错误信息不含 Key。

---

## 常见错误排查

| 现象 | 原因 / 解决 |
|---|---|
| `ConfigurationError: HY3_WORKSPACE_ROOT is required` | `analyze_project_context` 必须设置该变量为绝对路径 |
| `Hy3AuthenticationError` (401/403) | `HY3_API_KEY` 错误或过期；本地 vLLM 用 `EMPTY` |
| `Hy3RateLimitError` (429) | 触发限流，已自动重试；持续出现请降并发或调大 `HY3_MAX_RETRIES` |
| `Hy3TimeoutError` | 调大 `HY3_TIMEOUT_SECONDS`（上限 600）或降低 `HY3_REASONING_EFFORT` |
| `ModelOutputError: ... repair failed` | 模型返回的 JSON 不符合 schema，重试一次仍失败；可重跑或换 `high` 推理模式 |
| `WorkspaceAccessError: ... resolves outside the workspace` | 请求路径经 `..` 或符号链接逃出工作区，已被拒绝 |
| `FileTooLargeError` | 单文件/总量超限，缩小 `paths` 范围或调高上限 |
| 客户端看不到 Tool | 确认 `HY3_WORKSPACE_ROOT` 已设、进程能找到 `hy3-architecture-mcp`（`where hy3-architecture-mcp`） |

---

## 测试和开发

```bash
cd examples/hy3_architecture_mcp

# 全量测试（含 stdio 端到端集成测试，使用 mock Hy3 端点）
python -m pytest -q

# 仅路径安全测试
python -m pytest tests/test_path_security.py -q

# lint + 格式检查
python -m ruff check .
python -m ruff format --check .

# stdio 自检
python scripts/probe_stdio.py
```

测试覆盖（80 用例，3 个符号链接用例在无真实 symlink 的平台上跳过）：配置校验、Hy3 客户端
（重试/超时/认证/结构化输出/修复重试/日志脱敏）、5 个 Tool 的输入校验与错误传播、路径安全
（白名单/黑名单/`..` 穿越/绝对路径/敏感文件/大小/符号链接逃逸）、MCP stdio 端到端
（真实握手 + Tool 调用 + 工作区拒绝）。

---

## Demo 视频 / GIF

> 录制位（占位）：完成在 CodeBuddy / Cursor 中的真实录制后，将 60–90 秒 GIF/视频链接替换本节。
>
> 录制要求：展示 `clarify_requirements → generate_technical_proposal →
> review_technical_proposal → create_implementation_plan` 全流程，并在第二个客户端至少成功调用
> 一个核心 Tool；画面中 API Key、用户名、敏感本地路径必须打码。

`scripts/probe_stdio.py` 与 `examples/demo_workflow.py --mock` 可作为录制脚本：前者证明 stdio
启动与 Tool 发现，后者演示完整流水线的结构化输出。

---

## License

Apache 2.0，与仓库根目录 [LICENSE](../../LICENSE) 一致。
