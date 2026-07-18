# PR Draft & Acceptance Checklist

> 本文件为提交草稿，供最终审阅与填写实际验证结果后使用。**未获确认前不会自行提交或推送。**

## PR 标题（建议）

```
feat(examples): add Hy3-powered technical-proposal review MCP server (#3)
```

## PR 描述（草稿）

### 概述

新增一个基于 MCP 协议的 stdio Server，把 Hy3 封装为「技术方案评审」工作流，可被
CodeBuddy / WorkBuddy / Cursor / Cline 等任意支持 MCP 的客户端即插即用。

工作流：模糊需求 → `clarify_requirements` → `generate_technical_proposal` →
`review_technical_proposal` → `create_implementation_plan`，并可用 `analyze_project_context`
读取工作区内的可信本地文件作为上下文。

### 改动范围

全部新增文件位于 `examples/hy3_architecture_mcp/`，不修改仓库既有文件。

- `src/hy3_architecture_mcp/` — Server、Hy3 客户端、配置、异常、Schema、5 个 Tool、沙箱
- `tests/` — 80 个自动化测试（含 stdio 端到端集成测试，使用 mock Hy3 端点）
- `prompts/` — 5 个结构化输出提示词
- `examples/demo_workflow.py` — 端到端 Demo（`--mock` 无需 Hy3 即可演示全流程）
- `scripts/probe_stdio.py` — stdio + Tool 发现自检脚本
- `README.md` / `.env.example` / `pyproject.toml` / `LICENSE` / `.gitignore`

### 安装与运行

```bash
cd examples/hy3_architecture_mcp
pip install -e . --index-url https://pypi.org/simple/
hy3-architecture-mcp        # 或 python -m hy3_architecture_mcp
python scripts/probe_stdio.py            # 验证 stdio 与 Tool 发现
python examples/demo_workflow.py --mock   # 端到端 Demo（无需 Hy3 部署）
```

### 安全要点

- API Key 仅通过 `HY3_API_KEY` 环境变量传入，不硬编码、不入配置文件、日志脱敏。
- `analyze_project_context` 五重沙箱：工作区根边界 / 扩展名白名单 / 敏感文件黑名单 /
  大小限制 / 符号链接逃逸检查；`..` 穿越与绝对路径越界均被拒绝。
- 文件仅被读取后送 Hy3 分析，**绝不执行**。

### 验证结果

- `ruff check .` ✅  /  `ruff format --check .` ✅
- `pytest -q` ✅ 80 passed, 3 skipped（3 个符号链接用例在无真实 symlink 的 Windows 平台跳过，
  其安全逻辑由 `..` 穿越与绝对路径越界用例平台无关地覆盖）
- stdio 自检 ✅：通过官方 MCP 客户端 SDK 完成 `initialize` 握手，`tools/list` 返回全部 5 个 Tool
- 端到端 Demo ✅：`--mock` 模式跑通 4 个核心 Tool 的完整流水线，结构化输出正确，API Key 显示为 `***`
- stdio 集成测试 ✅：真实 Tool 调用经 stdio 传输 → Hy3Client → mock 端点 → 结构化结果返回；
  工作区外路径在 stdio 层被拒绝

### 关联 Issue

Closes #3

---

## 验收清单（逐项对照 Issue 要求）

| Issue 要求 | 状态 | 证据 |
|---|:---:|---|
| 基于 MCP Python SDK 实现 | ✅ | `mcp>=1.27,<2`，FastMCP 高级 API，stdio 传输 |
| 遵循 MCP 协议规范 | ✅ | 官方 SDK 自检：`initialize` + `tools/list` 通过 |
| Server 至少暴露 3 个 tool | ✅ | 5 个 tool |
| 每个 tool 含清晰名称/参数/功能说明 | ✅ | `tools/list` 返回 description + JSON Schema（含约束） |
| 内部调用 Hy3 API 完成核心推理 | ✅ | 4 个核心 tool 经 `Hy3Client` 调 OpenAI 兼容端点 |
| 额外接入数据源/工具 | ✅ | `analyze_project_context` 本地文件沙箱读取 |
| stdio 模式运行 | ✅ | `probe_stdio.py` 验证 |
| 代码不硬编码 API Key | ✅ | 仅 `HY3_API_KEY` 环境变量，日志脱敏，secret 扫描通过 |
| 至少 2 个 MCP 客户端验证 | ⚠️ | 协议层已用官方 MCP 客户端 SDK 验证（CodeBuddy/Cursor 同路径）；GUI 客户端实测需在本地完成 |
| CodeBuddy/WorkBuddy 项目级配置 | ✅ | README 含 `.mcp.json` 配置示例 + CLI 添加命令 |
| 可运行 Demo | ✅ | `examples/demo_workflow.py --mock` |
| 一键安装（pip install） | ✅ | `pip install -e .` 后 `hy3-architecture-mcp` 可执行 |
| 完整 README（安装/配置/使用示例） | ✅ | README 17 项齐全 |
| GIF 或视频 | ⚠️ | 待录制；`demo_workflow.py --mock` 与 `probe_stdio.py` 可作录制脚本 |

### 开发计划补充验收（plan.md 十五）

| 条目 | 状态 |
|---|:---:|
| 基于 rhinobird2026 分支开发 | ✅ |
| 使用 MCP Python SDK | ✅ |
| stdio 模式可运行 | ✅ |
| 至少 5 个 Tool 可被发现和调用 | ✅ |
| 四个核心 Tool 调用 Hy3 API | ✅ |
| 文件分析 Tool 有严格工作区边界 | ✅ |
| API Key 仅通过环境变量传入 | ✅ |
| pip install 后可执行 | ✅ |
| python -m 方式可执行 | ✅ |
| 两个不同 MCP 客户端验证成功 | ⚠️ 协议层已验证，GUI 实测待办 |
| 包含 CodeBuddy 或 WorkBuddy 项目级配置 | ✅ |
| 包含至少一个可运行 Demo | ✅ |
| README 完整 | ✅ |
| GIF 或视频可访问 | ⚠️ 待录制 |
| 自动化测试通过 | ✅ 80 passed / 3 skipped |
| lint 和格式检查通过 | ✅ |
| 不包含密钥或敏感文件 | ✅ |
| PR 目标分支为 rhinobird2026 | ✅（待推送时确认） |

---

## 仍需用户在本地完成的项（无法自动完成）

1. **GUI 客户端实测**：在 CodeBuddy（或 WorkBuddy）与 Cursor（或 Cline）中按 README 配置接入，
   至少在一个客户端跑通全流程、在第二个客户端跑通至少一个核心 Tool，记录客户端版本/系统/结果。
2. **录制 60–90 秒 GIF/视频**：展示完整流水线，画面对 API Key、用户名、敏感路径打码；
   完成后将链接填入 README 的「Demo 视频 / GIF」一节。
3. **推送与建 PR**：在 rhinobird2026 分支提交，目标分支 `rhinobird2026`（fork→PR）。
   `plan.md` 为开发计划文档，建议不纳入 PR（如需保留可放 `docs/`）。

## 已知限制

- 符号链接逃逸测试在无真实 symlink 的 Windows 环境（未开启开发者模式/管理员）会跳过；
  该安全路径由 `..` 穿越与绝对路径越界用例平台无关地覆盖，生产代码 `resolve()` + `_within` 逻辑正确。
- `analyze_project_context` 仅读取文本/代码类文件（白名单扩展名），二进制与非 UTF-8 文件跳过并告警。
- Hy3 端点需用户自行部署（vLLM/SGLang）；Demo 的 `--mock` 模式可在无部署时演示流水线与返回结构。
