# hy3-code-review-mcp

[![PyPI](https://img.shields.io/pypi/v/hy3-code-review-mcp)](https://pypi.org/project/hy3-code-review-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/hy3-code-review-mcp)](https://pypi.org/project/hy3-code-review-mcp/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

English: [README.md](README.md)

一个 MCP（Model Context Protocol）Server，把 **Hy3** 的 295B 参数推理模型作为即插即用的代码评审助手，接入任何兼容 MCP 的 AI 客户端。

插入 **Claude Code**、**CodeBuddy**、**Cursor**、**Cline** 或任意 MCP 客户端即可获得：

- 从 `git diff` 生成结构化、带严重级别标签的代码评审
- 单文件深度分析（安全 / 性能 / bug / 风格）
- 一条命令完成本地仓库的合并前评审

---

## 环境要求

| 依赖 | 说明 |
|---|---|
| Python ≥ 3.10 | |
| 一个 OpenAI 兼容的 API 端点 | 本地 Hy3（vLLM/SGLang）**或** [OpenRouter](https://openrouter.ai/) |
| `uv`（推荐）或 `pip` | 用于安装 |

### 方式一 —— 本地 Hy3（vLLM / SGLang）

按 [Hy3 部署指南](https://github.com/Tencent-Hunyuan/Hy3#deployment) 启动 vLLM 或 SGLang，
默认端点为 `http://127.0.0.1:8000/v1`。

### 方式二 —— OpenRouter（无需 GPU）

在 [openrouter.ai](https://openrouter.ai/) 领取免费 API key，然后设置：

```bash
export HY3_BASE_URL=https://openrouter.ai/api/v1
export HY3_API_KEY=<你的-openrouter-key>
export HY3_MODEL=tencent/hy3:free   # 追求速度可换 google/gemini-2.5-flash
```

---

## 安装

### 方式 A —— `uvx` 一行命令（无需安装）

```bash
uvx hy3-code-review-mcp
```

### 方式 B —— `pip install`

```bash
pip install hy3-code-review-mcp
hy3-code-review-mcp          # 以 stdio 启动 MCP server
```

### 方式 C —— 源码安装

```bash
git clone https://github.com/mkun-dev/hy3-code-review-mcp
cd hy3-code-review-mcp
pip install -e .
hy3-code-review-mcp
```

---

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `HY3_BASE_URL` | `http://127.0.0.1:8000/v1` | vLLM / SGLang / OpenRouter 端点 |
| `HY3_API_KEY` | `EMPTY` | API key（本地服务用 `"EMPTY"`） |
| `HY3_MODEL` | `hy3` | 模型名（如 `hy3`、`tencent/hy3:free`、`google/gemini-2.5-flash`） |
| `HY3_ALLOWED_ROOTS` | *(未设置)* | 可选：`analyze_file` 允许读取的目录列表（冒号分隔） |

**绝不硬编码 API key。** 只通过环境变量传入。

---

## MCP 客户端接入

各客户端的详细步骤见 [`docs/clients/`](docs/clients/)，配置模板见 [`examples/clients/`](examples/clients/)：

- [Claude Code](docs/clients/claude-code.md)
- [Cline](docs/clients/cline.md)
- [Cursor](docs/clients/cursor.md)
- [CodeBuddy / WorkBuddy](docs/clients/codebuddy-workbuddy.md)

演示录屏见 [`docs/demos/`](docs/demos/)。

---

## 可用工具

### `review_diff`
评审一段 git diff 文本或 `.diff`/`.patch` 文件。

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `diff` | string | 二选一 | — | 原始 diff 文本（优先于 `diff_file`） |
| `diff_file` | string | 二选一 | — | `.diff` / `.patch` 文件路径 |
| `context` | string | 否 | — | 本次改动的背景说明 |
| `reasoning_effort` | `"no_think"` \| `"low"` \| `"high"` | 否 | `"high"` | Hy3 推理深度 |

### `analyze_file`
对单个源码文件做深度分析。

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `file_path` | string | 是 | — | 源码文件路径 |
| `focus` | `"security"` \| `"performance"` \| `"style"` \| `"bugs"` \| `"all"` | 否 | `"all"` | 关注点 |
| `reasoning_effort` | string | 否 | `"high"` | Hy3 推理深度 |

### `git_diff_review`
在本地仓库自动运行 `git diff <base_branch>` 并生成完整评审。

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `repo_path` | string | 是 | — | git 仓库绝对路径 |
| `base_branch` | string | 否 | `"main"` | 对比的基线分支 |
| `reasoning_effort` | string | 否 | `"high"` | Hy3 推理深度 |

---

## 工作原理

```
MCP 客户端 (Claude Code / CodeBuddy / Cursor / Cline)
        │  stdio 传输
        ▼
hy3-code-review-mcp  (本 server)
        │
        ├── 读本地文件 / 运行 git 命令
        │
        └── OpenAI 兼容 HTTP 调用
                    │
                    ▼
            Hy3 API (vLLM / SGLang / OpenRouter)
```

- 传输：**stdio**（本地，零网络暴露）
- 默认使用 Hy3 的 `reasoning_effort="high"` 做深度评审
- 256K 上下文窗口，大 diff 和整文件不截断
- 所有 API key 走环境变量，绝不硬编码

---

## 安全

- 若设置了 `HY3_ALLOWED_ROOTS`，文件读取被限制在其中（防路径穿越）
- `base_branch` 用 `^[A-Za-z0-9][A-Za-z0-9._/-]*$` 校验（防 git 注入）
- `--no-ext-diff` 与 `GIT_CONFIG_NOSYSTEM=1` 阻断恶意仓库配置导致的 RCE
- 向非本地主机的明文 HTTP 会触发 stderr 警告
- 返回客户端前对错误信息做脱敏（不泄露内部路径）

---

## 许可证

Apache 2.0 —— 见 [LICENSE](LICENSE)。
