# CtxPilot / 续舱

> 跨会话边界的「上下文连续性层」—— 让 opencode、codex 等编程 agent 在重启、换 agent、时间断层后，不浪费上下文重读整个仓库。
>
> **Powered by [Tencent-Hunyuan/Hy3](https://github.com/Tencent-Hunyuan/Hy3)** — 腾讯混元 Hy3 大模型。
> 本仓库是犀牛鸟实战 issue **#4「Build a vibe-coded application powered by Hy3」** 的参赛作品。

---

## 🇬🇧 Abstract (English)

**CtxPilot** is a cross-session *context-continuity layer* for coding agents (opencode, codex, …).
When an agent restarts or you switch agents, you normally re-read the whole repo and lose state.
CtxPilot captures project state from agent session logs + git as ground truth, then asks **Hy3 (via API)**
to compress it into a portable `HANDOFF.md` and an onboarding *brief*. A new session loads that instead
of re-reading everything — saving tokens and keeping continuity across agent boundaries.

Hy3's role is strictly **API-based** (OpenAI-compatible `/chat/completions`): summarize, bridge context,
generate briefs. No fine-tuning, no local inference, no training.

---

## 📌 痛点：为什么需要它

你用很多家的 agent（opencode、codex…），常遇到两种「断档」：

- **场景 A · 同 agent 重启**：一个长会话漂移到后面忘了前面，或进程崩了重开，又得从头读仓库、重新对齐。
- **场景 B · 换 agent 交接**：opencode 做了一半想切到 codex（或反过来），新 agent 对上下文一无所知。

根因是 **agent 之间、会话之间没有可移植的「状态快照」**。CtxPilot 就是这块「续舱」。

---

## 🤖 Hy3 在这个应用里扮演什么角色

Hy3 是 CtxPilot 的**唯一智能来源**，但**只通过 API 调用**（符合 issue 要求，绝不微调/本地推理）：

| 能力 | 由谁完成 | 说明 |
|---|---|---|
| 项目状态**摘要 / 压缩** | **Hy3** | 把 git 真值 + 多 agent 会话历史压缩成结构化 `HANDOFF.md`（N2） |
| 跨 agent **上下文桥接** | **Hy3** | 生成可移植交接信封 `HandoffExport`，让 codex 读懂 opencode 留下的状态（N4） |
| 新会话**启动简报** | **Hy3** | 生成 onboarding brief：「先看哪 3 件事 / 当前阻塞 / 建议先读文件」（N7） |
| 会话**漂移检测**（二期） | **Hy3** | 识别循环 / 矛盾 / 未关闭的报错（N3） |
| 记忆**问答**（二期） | **Hy3** | 轻量 RAG + 引用式回答（N5） |

调用方式（全部收敛在 `src/ctxpilot/hy3/client.py` 一处）：

- 端点：`HY3_BASE_URL`（云端 `https://tokenhub.tencentmaas.com/v1`，或自建 vLLM/SGLang）
- 模型：`hy3`，`reasoning_effort` 可选 `no_think` / `low`（常规） / `high`（复杂任务）
- 协议：OpenAI 兼容 `POST {base_url}/chat/completions`

> **安全**：发给 Hy3 的转录内容一律当作**数据**而非指令（防提示注入）；system prompt 要求模型忽略嵌入指令。写入 `HANDOFF.md` 前默认**密钥脱敏**。

---

## ✨ 功能（一期 MVP = N1 + N2 + N4 + N7）

- **N1 零负担采集**：只读 `~/.codex`、`~/.local/share/opencode` 等会话目录 + git 真值（分支 / 近期 commit / 改动文件），**不向 agent 内部塞任何钩子或指针**。
- **N2 项目状态快照**：调 Hy3 生成 `HANDOFF.md`（目标 / 任务 / 决策 / 已知问题 / 约定），脱敏后写入项目根。
- **N4 跨 agent 交接**：`export` 生成可移植信封，`import` 产出可粘贴给新 agent 的首条上下文。
- **N7 启动简报**：新会话一开始就读到「先看哪 3 件事 / 当前阻塞 / 建议文件」。

二期（N3 漂移看门狗 / N5 记忆问答 / N6 省 token 计量）已预留 service 接口，加文件即接，不回溯改一期。

---

## 🏗️ 架构（UI 与逻辑彻底解耦）

```
CLI (typer) ─┐
             ├─▶ CtxPilot 门面 ─▶ Services(N1/N2/N4/N7) ─▶ adapters / hy3_client / git
WebUI ─▶ FastAPI ─┘
```

- **Core 不知道 UI 存在**：CLI 与 Web 都只调 `CtxPilot` 一个门面，绝不直接碰领域层。
- **加 agent = 加一个适配器文件**：实现 `AgentAdapter` 3 个方法即可，核心引擎零改动。
- **Hy3 调用全收敛一处**：换端点 / 换推理模式只动 `hy3/client.py`。

详见 [`DESIGN.md`](./DESIGN.md)。

---

## 🚀 快速开始

### 1. 安装

```bash
cd Hy3_APP
python -m venv .venv && .venv\Scripts\activate        # Windows；macOS/Linux 用 source .venv/bin/activate
pip install -e ".[dev]"                                 # 运行依赖 + 测试依赖；[qt] 额外装 PySide6 桌面端
```

### 2. 配置 Hy3 Key

```bash
cp .env.example .env
# 编辑 .env，填入你的 HY3_API_KEY（.env 已被 .gitignore 忽略，绝不进仓库）
```

`.env` 内容示例：

```ini
HY3_BASE_URL=https://tokenhub.tencentmaas.com/v1
HY3_API_KEY=your-hy3-api-key-here
HY3_MODEL=hy3
HY3_REASONING_EFFORT=low
```

> Key 仅从环境变量 / 本地 `.env` 读取，WebUI 的「设置」页只把 Key 写进本地 `.env`，**绝不回传任何云端**。

### 3. 运行 WebUI（推荐，自动发现项目）

```bash
python -m ctxpilot.cli serve --host 127.0.0.1 --port 8000
# 浏览器打开 http://127.0.0.1:8000
```

打开即**自动扫描本机已有 agent 的会话历史**，推断出你正在做的项目位置（无需手填项目根），
列出可监控的 agent，并自动开始监控。选一个项目即可「生成 HANDOFF」「启动简报」「导出」。

### 4. 或用 CLI

```bash
python -m ctxpilot.cli scan                 # 列出自动发现的项目
python -m ctxpilot.cli snapshot D:/VS_Project   # 调 Hy3 生成 HANDOFF.md
python -m ctxpilot.cli brief   D:/VS_Project   # 生成启动简报
python -m ctxpilot.cli export  D:/VS_Project --target codex   # 跨 agent 交接信封
python -m ctxpilot.cli qt                     # 可选：PySide6 桌面端
```

---

## 🎬 两个 Demo 如何走通（证明 Hy3 的角色）

**Demo 1 — 同 agent 重启（场景 A）**
```
opencode 长会话（漂移）
  → ctxpilot snapshot   (git 真值 + 会话历史 → Hy3 → HANDOFF.md，脱敏写入)
  → 新 opencode 会话 import   (读 HANDOFF.md 而非重读仓库)
  → ctxpilot brief      (Hy3 生成启动简报：先看 3 件事 / 当前阻塞)
  → 新会话立刻对齐、修 bug、零重读
```

**Demo 2 — 跨 agent 交接（场景 B）**
```
opencode 做一半
  → ctxpilot export --target codex
  → codex 会话 import  (读 HANDOFF.md 而非整个仓库)
  → codex 无缝续上
```

两条数据流都依赖 Hy3 完成 **摘要 / 压缩、跨 agent 上下文桥接、简报生成**。

---

## 🔒 安全设计

| 风险 | 措施 |
|---|---|
| 日志含密钥 | 写 `HANDOFF.md` / 发 Hy3 前默认 `security.sanitize` 脱敏（sk-/AKIA/api_key=/token/私钥头/.env） |
| 上下文外发 | 端点可配；敏感仓库用本地 vLLM |
| `HANDOFF.md` 误提交 | 默认写进 `.gitignore`，不自动 commit |
| 误写 agent 库 | 适配器**只读** `~/.codex` / `~/.local/share/opencode`，绝不改其 DB |
| Key 泄露 | 仅 env/.env 读取；`.env` 进 `.gitignore`；WebUI 只写本地 |
| 转录提示注入 | 转录当数据；system prompt 要求忽略嵌入指令 |
| 供应链 | 依赖最小化、锁版本；只解析文件，绝不执行 agent 命令 |

---

## 📂 目录结构

```
Hy3_APP/
├─ pyproject.toml
├─ .env.example
├─ .gitignore            # 忽略 .venv / .env / HANDOFF.md
├─ DESIGN.md             # 业务分解与解耦设计
├─ ISSUE4_REQUIREMENTS.md# issue 硬性要求
├─ README.md             # 本文
└─ src/ctxpilot/
   ├─ config.py          # Config + env/.env 读取
   ├─ models.py          # 领域模型（含 HANDOFF 结构）
   ├─ core.py            # CtxPilot 门面（UI↔逻辑 唯一边界）
   ├─ security.py        # 脱敏 + gitignore
   ├─ hy3/client.py      # Hy3 OpenAI 兼容封装（唯一出口）
   ├─ ingestion.py       # 采集编排 + git 真值
   ├─ adapters/          # opencode.py / codex.py（可扩展）
   ├─ services/          # snapshot(N2) / handoff(N4) / brief(N7) / drift·memory·savings(二期)
   ├─ cli.py             # typer 入口
   ├─ qt/                # PySide6 桌面端（可选）
   └─ web/               # FastAPI + 纯前端 static/
```

---

## 🧪 开发

```bash
.venv\Scripts\activate
pytest -q                 # 66 个测试（3 个 Qt 用例在缺 PySide6 时 skip）
```

测试用 `FakeHy3` 与 `httpx.MockTransport` 隔离真实 API；真实 agent 目录只读，不依赖任何外部服务即可全绿。

---

## 🗺️ 路线图

- [x] 一期 MVP：N1 采集 / N2 快照 / N4 交接 / N7 简报
- [ ] 二期：N3 漂移看门狗 / N5 记忆问答 / N6 省 token 计量
- [ ] 更多 agent 适配器（Claude Code、Aider、Cursor…）
- [ ] IDE 插件表现层（复用同一 `CtxPilot` 门面）

---

## 📄 许可证

本应用遵循与 Hy3 仓库一致的 [Apache 2.0](../LICENSE)。

## 🔗 参考

- Issue：[#4 Build a vibe-coded application powered by Hy3](https://github.com/Tencent-Hunyuan/Hy3/issues/4)
- 模型：[Tencent-Hunyuan/Hy3](https://github.com/Tencent-Hunyuan/Hy3)
