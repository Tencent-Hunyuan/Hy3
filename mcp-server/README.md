# hy3-mcp — Hy3 研究与代码助手 MCP Server

<p align="left">
  <a href="README_EN.md">English</a> | 中文
</p>

**hy3-mcp** 是一个基于 [MCP（Model Context Protocol）](https://modelcontextprotocol.io) 的 stdio Server：把腾讯混元 **Hy3** 大模型的能力封装成 5 个即插即用的 tool，任何支持 MCP 的客户端（CodeBuddy / WorkBuddy / Cursor / Cline / Claude Code 等）**零开发**即可接入 Hy3 完成代码评审、知识库问答、数据分析与深度研究。

| Tool | 场景 | Hy3 承担的核心推理 | 数据源 |
|---|---|---|---|
| `review_code` | 代码评审 | 审阅 unified diff / 源码，输出按严重程度排序的评审意见 | 本地文件（沙箱） |
| `ask_docs` | 知识库问答 | 仅依据检索出的文档片段作答并给出 `(file#chunk)` 引用 | 本地文档 + 确定性检索 |
| `analyze_data` | 数据分析 | 基于确定性数据画像撰写分析叙事与图表建议 | 本地 CSV / JSON |
| `deep_research` | 深度研究 | 综合多来源证据，产出带编号引用的研究结论 | 可插拔搜索 + 本地文件 |
| `hy3_status` | 诊断 | 无 LLM 调用；报告模式/模型/用量，适合接入后第一个演示调用 | — |

外部数据源恰好 2 个（对应题面「可额外接入 1~2 个数据源」）：**① 沙箱化本地文件读取**（`HY3_MCP_ROOT` 之外一律拒绝，防路径逃逸/软链逃逸，大小上限、坏编码不崩溃）；**② 可插拔搜索**（默认 `offline` 离线 stub 零依赖可跑，`tavily` 走环境变量 `TAVILY_API_KEY`，一行代码可扩展新搜索源）。

## 演示 GIF

![demo](assets/demo.gif)

> 本 GIF 为**真实录制**：脚本驱动真实的 `python -m hy3_mcp` 子进程、用独立的裸 JSON-RPC 客户端走完整 MCP 流程。因开发机上没有 Hy3 API Key，录制时使用内置**离线确定性 fake 后端**，画面已用 `OFFLINE DEMO MODE (fake Hy3 backend)` 明确标注 —— 不是真实模型输出。配置真实 Key 后可用同两个脚本重录（见[重录演示](#重录演示)）。

## Hy3 的角色与设计原则

- **核心推理全部由 Hy3 完成**：4 个业务 tool 都经由 openai SDK 调用 Hy3 的 OpenAI 兼容接口（`model=hy3`，推荐采样 `temperature=0.9, top_p=1.0`），并按任务透传 `reasoning_effort`（`deep_research`/`review_code` 默认 `high`，其余 `no_think`，可用 `HY3_REASONING_EFFORT` 全局覆盖）——与上游 README 的 `chat_template_kwargs` 约定完全一致。
- **LLM 输出永不解析、只呈现**：所有结构化字段（diff 统计、启发式风险标记、数据画像、引用列表）由纯 Python 确定性计算并进入 MCP `structuredContent`/`outputSchema`；Hy3 只产出 `markdown` 叙事字段。真实后端下没有任何 JSON-parse 脆弱性，离线后端下测试全确定。
- **离线模式与真实模式共享 100% 生产代码路径**：离线只是把 HTTP transport 换成进程内 `httpx.MockTransport`（openai SDK 的请求组装、超时、usage 统计原样执行），一个环境变量即可切换，**缺 Key 永不崩溃**（开箱即可在客户端里试玩）。

## 安装（一键）

要求 Python ≥ 3.10。两条通道任选：

```bash
# 通道 A：免安装直接运行（推荐试用）
uvx --from /ABS/PATH/TO/Hy3/mcp-server hy3-mcp --selfcheck

# 通道 B：pip 安装为 console script
cd Hy3/mcp-server && pip install .
hy3-mcp --selfcheck
```

`--selfcheck` 会在进程内启动离线 server、实际调用 `hy3_status` 与 `review_code` 并打印 `PASS/FAIL`——一条命令验证安装成功。不需要发布到 PyPI。

## 配置（全部环境变量，零硬编码）

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `HY3_API_BASE` | `http://127.0.0.1:8000/v1` | Hy3 的 OpenAI 兼容端点 |
| `HY3_API_KEY` | （空） | API Key；**只从环境变量读取**，自建端点可不设（等价 `EMPTY`） |
| `HY3_MODEL` | `hy3` | 模型名（对应 vLLM `--served-model-name hy3`） |
| `HY3_MCP_OFFLINE` | （空） | `1/true/yes` 强制离线演示模式 |
| `HY3_MCP_ROOT` | 当前目录 | 本地文件沙箱根：所有文件读取被限制在该目录内 |
| `HY3_MCP_DOCS_DIR` | 同沙箱根 | `ask_docs` 的默认文档目录（相对沙箱根；也可为绝对路径——沙箱根外的绝对目录会成为附加只读沙箱根） |
| `HY3_SEARCH_PROVIDER` | `offline` | 搜索源：`offline`（内置 stub）/ `tavily`（需 `TAVILY_API_KEY`） |
| `HY3_REASONING_EFFORT` | 按工具 | `no_think` / `low` / `high`，设置后全局覆盖各工具默认值 |
| `HY3_TEMPERATURE` / `HY3_TOP_P` | `0.9` / `1.0` | 上游 README 推荐采样参数 |
| `HY3_TIMEOUT_SECONDS` / `HY3_MAX_TOKENS` | `120` / `2048` | 请求超时 / 最大生成长度 |

**模式判定**（`hy3_status` 可随时查看当前模式）：

| 条件 | 模式 |
|---|---|
| `HY3_MCP_OFFLINE` 为真（或 CLI `--offline`） | `offline`（强制） |
| 否则设置了 `HY3_API_BASE` 或 `HY3_API_KEY` | `real` |
| 否则（什么都没配） | `offline` + stderr 提示横幅，**不崩溃** |

**两种真实后端接法**：

```bash
# ① 自建 vLLM / SGLang（上游 README 快速开始;无需真实 Key）
export HY3_API_BASE=http://127.0.0.1:8000/v1     # vLLM: --served-model-name hy3

# ② 腾讯云 OpenAI 兼容端点（以云文档为准）
export HY3_API_BASE=https://api.hunyuan.cloud.tencent.com/v1
export HY3_API_KEY=<你在控制台申请的 Key>
```

## 使用示例

```bash
# 直接以 stdio 模式启动（一般由 MCP 客户端拉起，无需手动运行）
HY3_MCP_OFFLINE=1 python -m hy3_mcp          # 或 hy3-mcp / uvx --from . hy3-mcp

# 无 SDK 的裸 JSON-RPC 客户端跑一遍完整流程（离线、零依赖）
python scripts/raw_stdio_client.py
```

在客户端中的可运行 demo 话术（配好后直接输入）：

> 请用 hy3 的 `review_code` 工具审查 `examples/diffs/demo.diff`，总结主要风险。
> 用 `ask_docs` 在 `examples/docs` 里回答：Hy3 的上下文长度是多少？
> 用 `analyze_data` 分析 `examples/data/sales_sample.csv` 并给出图表建议。

## 客户端接入

现成配置见 [`clients/`](clients/)。将其中的 `/ABS/PATH/TO/Hy3/mcp-server` 改为你的绝对路径即可。

### CodeBuddy / WorkBuddy（项目级配置 + CLI 命令）

项目级 `mcp.json`（完整文件见 [`clients/codebuddy.mcp.json`](clients/codebuddy.mcp.json)，内含免 Key 离线试玩变体 `hy3-offline-demo`）：

```json
{
  "mcpServers": {
    "hy3": {
      "command": "uvx",
      "args": ["--from", "/ABS/PATH/TO/Hy3/mcp-server", "hy3-mcp"],
      "env": {
        "HY3_API_BASE": "http://127.0.0.1:8000/v1",
        "HY3_API_KEY": "${env:HY3_API_KEY}",
        "HY3_MODEL": "hy3",
        "HY3_MCP_ROOT": "${workspaceFolder}"
      }
    }
  }
}
```

CodeBuddy Code CLI 一行添加：

```bash
codebuddy mcp add hy3 -e HY3_API_BASE=http://127.0.0.1:8000/v1 \
  -e HY3_API_KEY=$HY3_API_KEY -e HY3_MCP_ROOT=$PWD \
  -- uvx --from /ABS/PATH/TO/Hy3/mcp-server hy3-mcp
```

启动命令 ✓ 环境变量 ✓ 可运行工具调用 demo ✓（见上节话术；第一次建议先调 `hy3_status` 验证连通）。

### Cursor / Cline / Claude Code

- Cursor：把 [`clients/cursor.mcp.json`](clients/cursor.mcp.json) 内容并入项目 `.cursor/mcp.json`。
- Cline：把 [`clients/cline.mcp.json`](clients/cline.mcp.json) 内容并入 `cline_mcp_settings.json`。
- Claude Code：运行 [`clients/claude-code.sh`](clients/claude-code.sh)（内含离线试玩与单次调用验证命令）。

### 客户端验证矩阵（诚实声明）

| 客户端 | 状态 | 证据 |
|---|---|---|
| 官方 MCP Python SDK stdio 客户端 | ✅ 开发机已验证 | `tests/test_stdio_e2e_sdk.py`（initialize / tools/list / 全部 5 tool 调用 / 错误路径） |
| 独立裸 JSON-RPC stdio 客户端（零 mcp 依赖） | ✅ 开发机已验证 | `scripts/raw_stdio_client.py` + `tests/test_stdio_e2e_raw.py` |
| **Claude Code CLI 2.1.197（真实第三方客户端）** | ✅ 开发机已验证 | `claude mcp add` 健康检查 `✔ Connected`；`claude -p` 实际调用 `hy3_status` 返回 `mode=offline, model=hy3` |
| **Gemini CLI 0.51.0（真实第三方客户端）** | ✅ 开发机已验证（连接级） | `gemini mcp add hy3-mcp uvx --from <repo>/mcp-server hy3-mcp` 后 `gemini mcp list` ⇒ `✓ hy3-mcp … - Connected`（完成 MCP initialize 握手；工具实调证据见上行 Claude Code CLI） |
| CodeBuddy / WorkBuddy（GUI） | 🔶 配置已备好，需本地验证 | 开发机无 GUI；按上节 3 步接入后先调 `hy3_status` |
| Cursor / Cline（GUI） | 🔶 配置已备好，需本地验证 | 同上 |

## 测试方法

```bash
cd mcp-server
python -m pytest tests -q        # 74 个测试,全离线确定性,约 16s
```

覆盖：模式判定矩阵、fake 后端 wire-format/确定性/`reasoning_effort` 透传、沙箱逃逸与大小/编码防御、检索确定性（含中文 bigram）、搜索源工厂与 Tavily 错误路径（MockTransport,不发真网络）、5 个 tool 的进程内与双客户端 stdio e2e、打包元数据、**无硬编码密钥扫描**。

## 架构

```
mcp-server/
├── src/hy3_mcp/
│   ├── server.py          # FastMCP 组装 + CLI(--version/--offline/--selfcheck)
│   ├── settings.py        # 纯 env 配置;Key 永不进入 Settings(只有布尔存在位)
│   ├── hy3_client.py      # openai AsyncOpenAI 封装;用量统计;错误→ToolError
│   ├── fake_backend.py    # 离线确定性 fake(httpx.MockTransport,OpenAI wire 格式)
│   ├── prompts.py / schemas.py
│   ├── tools/             # 5 个 tool(review/ask/analyze/research/status)
│   └── sources/           # 数据源①沙箱文件+检索;数据源②可插拔搜索
├── clients/               # CodeBuddy/WorkBuddy、Cursor、Cline、Claude Code 配置
├── examples/              # 演示 diff/文档/CSV/JSON(数字与测试逐项对齐)
├── scripts/               # 裸 JSON-RPC 客户端、GIF 录制/渲染
└── tests/                 # 74 个离线确定性测试
```

扩展新搜索源：在 `sources/search.py` 实现 `SearchProvider` 协议并注册进 `_FACTORIES` 即可（参考 `TavilySearch`，Key 一律走环境变量）。

## 重录演示

```bash
# 渲染 GIF 需要 Pillow(可选 extra,核心安装不包含):
pip install '.[demo]'
# 离线(与仓库内 GIF 相同)
python scripts/record_demo.py && python scripts/render_gif.py
# 真实模型:配置 HY3_API_BASE/HY3_API_KEY 后重跑同两条命令
```

## FAQ

- **为什么客户端里看到 OFFLINE DEMO MODE？** 未配置 `HY3_API_BASE`/`HY3_API_KEY` 时自动进入离线演示模式（这是特性：无 Key 也能体验全部工具）。配置后自动切换真实模式，`hy3_status` 可确认。
- **stdout 上能打印日志吗？** 不能。stdio 模式下 stdout 是 MCP 协议通道，本项目所有横幅/诊断都走 stderr——自研 MCP server 最常见的翻车点。
- **Key 会被记录吗？** 不会。Key 只在构建 HTTP 客户端时从环境变量读取，从不进入 `Settings`/日志/`hy3_status`（只报告 `api_key_present` 布尔值），测试有专项断言。
- **`path escapes sandbox root` 报错？** 所有文件参数被限制在 `HY3_MCP_ROOT` 内（含软链解析后）。把沙箱根指向你的项目目录即可。

## License

Apache-2.0（继承仓库根 [LICENSE](../LICENSE)）。
