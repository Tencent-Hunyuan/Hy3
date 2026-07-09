# 🏛 Codebase Archaeologist

> **Hy3 驱动的智能代码仓库理解引擎** — 将数周的人工代码阅读压缩为分钟级的自动化架构分析。

<p align="center">
  <img src="https://img.shields.io/badge/Hy3-Powered-6366f1?style=flat-square" alt="Hy3 Powered">
  <img src="https://img.shields.io/badge/ReAct-Agent-34d399?style=flat-square" alt="ReAct Agent">
  <img src="https://img.shields.io/badge/Context-256K-fbbf24?style=flat-square" alt="256K Context">
  <img src="https://img.shields.io/badge/Output-Structured_JSON-f87171?style=flat-square" alt="Structured Output">
  <img src="https://img.shields.io/badge/License-Apache_2.0-blue?style=flat-square" alt="License">
</p>

---

## 目录

- [项目简介](#项目简介)
- [竞赛要求对照](#竞赛要求对照)
- [为何选择 Hy3](#为何选择-hy3)
- [系统架构](#系统架构)
- [Hy3 调用模式矩阵](#hy3-调用模式矩阵)
- [技术栈与依赖](#技术栈与依赖)
- [快速开始](#快速开始)
- [部署方案](#部署方案)
- [两个端到端 Demo](#两个端到端-demo)
- [CodeBuddy 协作记录](#codebuddy-协作记录)
- [项目结构](#项目结构)
- [License](#license)

---

## 项目简介

接手一个陌生仓库时，真正的问题不是"看不懂某一行的语法"，而是：

* 不知道从哪里开始读
* 跨文件函数调用链追踪困难
* 隐性架构假设难以发现
* 设计模式识别需要经验积累
* PR Review 只看到 diff，看不到架构影响

**Codebase Archaeologist** 解决这些问题。**只输入一个 GitHub 仓库 URL**，系统自动完成：

1. **架构反解** — 推断模块职责、分层结构、数据流向
2. **入口点定位** — 识别关键启动路径与核心调用链
3. **设计模式识别** — 标注代码中的设计模式与架构风格
4. **风险嗅探** — 发现循环依赖、God Class、重复抽象等结构问题
5. **部署指南生成** — 基于分析结果自动生成部署文档
6. **可交互追问** — 分析完成后可针对任意模块/函数进行对话式追问

---

## 竞赛要求对照

本项目参加 **"Build a vibe-coded application powered by Hy3"** 犀牛鸟实战课题，满足全部要求：

| 要求 | 本项目实现 |
|------|----------|
| ✅ 全程 API 调用，不做训练/微调/本地推理 | 100% 通过 Hy3 OpenAI 兼容 API 调用，零模型文件本地部署 |
| ✅ 至少 1 个可交互前端 | React 19 + Tailwind CSS Web UI，D3 力导向图 + Mermaid 架构图 |
| ✅ 至少 2 个端到端 Demo 流程 | Demo 1: 仓库深度考古 · Demo 2: PR 架构影响分析 |
| ✅ 项目开源 | Apache 2.0 协议 |
| ✅ README 写明 Hy3 在系统中承担的角色 | 详见 [Hy3 调用模式矩阵](#hy3-调用模式矩阵) |
| ✅ 记录 CodeBuddy 协作内容 | 详见 [CodeBuddy 协作记录](#codebuddy-协作记录) |
| ✅ 可运行 | 本地一键启动，CLI + Web 双入口 |

---

## 为何选择 Hy3

> "如果一个 LLM 调换为其他模型也能跑出相近效果，那这个项目就没有展示 Hy3 的独特价值。"

### Hy3 的 5 项核心能力如何支撑本项目

| Hy3 能力 | 使用位置 | 承担角色 | 为什么非它不可 |
|----------|---------|---------|---------------|
| **深度推理** (`reasoning_effort=high`) | Phase 2.5 策略规划 · Phase 3.5 一致性校验 | 制定分批分析策略，检测跨批次矛盾 | 代码架构推理是典型的多步长链推理任务——要从文件清单、目录树、PageRank 排名中推理出最优的分析批次划分。普通 LLM 容易产生"看起来对但经不起推敲"的架构结论 |
| **256K 上下文** | Phase 3 批量分析 · Phase 3.5 全量一致性检查 | 10~30 个关联文件一次性交叉理解 | 跨文件调用链追踪、分层验证、循环依赖检测都需要同时"看见"多个完整文件的内容。上下文不够大就得频繁截断，分析质量断崖式下降 |
| **Function Calling** | Phase 3 ReAct Agent 循环 | 自主决定调用工具（grep / read / AST / dep_graph）获取信息 | 这是 Agent 自主决策闭环的展示，不是被动喂数据给 LLM。模型分析到一个 import 时如果想知道被 import 的模块具体做了什么，它会自己调 `file_read` 去读 |
| **Structured Output** (`response_format`) | Phase 4 知识综合 | 输出符合 JSON Schema 的 `ArchitectureReport` | 前端直接渲染 D3 图、Mermaid 图、风险卡片，无需额外 parser 或格式修正。Schema 中包含模块、调用链、设计模式、风险等 6 个顶级字段 |
| **Prompt Cache** (`prompt_cache_key`) | 全局所有调用 | 缓存 System Prompt，追问成本降约 75% | 分析完仓库后在追问阶段，System Prompt 从缓存读取而非重新计算，用户只需为增量 context 付费 |

### 四个调用模式覆盖完整分析链路

| 模式 | reasoning_effort | tool_choice | 使用阶段 | 每仓库调用次数 |
|------|-----------------|-------------|---------|-------------|
| **Planner** | `high` | `auto` | Phase 2.5 策略规划 · Phase 3.5 一致性校验 | 1-2 次 |
| **Reader** | `medium` | `none` | QA 追问模式（非流式） | 按需 |
| **ReAct Agent** | `medium` → `low` | `auto` → `none` | Phase 3 分批代码分析 | 每批次 1-3 轮 |
| **Synthesizer** | `low` | `none` | Phase 4 结构化报告生成 | 1 次 |

---

## 系统架构

### 核心设计：如何用单个 API 分析任意大小的仓库

250K token 的上下文窗口虽然大，但稍微大一点的仓库 token 总量就会超过上限。我们设计了一套**分而治之 + 上下文接力**的六阶段管线：

```
用户输入 GitHub URL
    │
    ▼
┌──────────────────────────────────────────────────┐
│  Phase 1 — Repo Ingest (纯工程，零 API 消耗)       │
│  git clone → 文件扫描 → 语言/框架自动检测          │
│  产出: FileManifest (文件清单 + token 估算)         │
├──────────────────────────────────────────────────┤
│  Phase 2 — Dependency Graph (纯工程，零 API 消耗)  │
│  AST import 解析 → NetworkX PageRank → 循环检测    │
│  产出: DepGraph (精确的模块依赖图)                  │
├──────────────────────────────────────────────────┤
│  Phase 2.5 — Strategy Planning (Hy3 Planner)       │
│  推理: 哪些文件放同一批？为什么？批次间顺序？       │
│  产出: AnalysisPlan (包含分批策略和关注维度)        │
├──────────────────────────────────────────────────┤
│  Phase 3 — Batch Analysis (Hy3 ReAct Agent)        │
│  每批文件 → Hy3 自主调用工具分析 → 摘要传给下批     │
│  产出: BatchFindings[] (每批的结构化发现)           │
├──────────────────────────────────────────────────┤
│  Phase 3.5 — Consistency Check (Hy3 Planner)       │
│  全量 BatchFindings 交叉验证 → 消除矛盾、统一术语   │
│  产出: ConsistencyReport                           │
├──────────────────────────────────────────────────┤
│  Phase 4 — Knowledge Synthesis (Hy3 Synthesizer)   │
│  综合研判 → 严格 JSON Schema 输出                   │
│  产出: ArchitectureReport (含 6 个维度的完整报告)    │
├──────────────────────────────────────────────────┤
│  Phase 5 — Artifact Generation (纯工程)            │
│  报告 JSON → D3 力导向图 + Mermaid 架构图 + 风险卡片 │
└──────────────────────────────────────────────────┘
```

关键设计要点：

* **上下文接力机制**：Phase 3 的每批分析完成后，生成结构化的批次摘要（模块角色、关键抽象、数据流、风险、下批线索），这些摘要作为下一批的上下文输入。解决了多批次分析的天然缺陷——各批次之间不是孤岛。
* **本地静态分析 + AI 推理互补**：import 关系这种精确的东西走本地 AST（零幻觉），架构风格判断、设计模式识别、风险嗅觉走 Hy3。Phase 4 结束后还会用本地 DepGraph 数据修正 Hy3 输出的依赖关系字段。
* **Commit 级缓存**：分析过的 commit hash 会持久化到 `~/.archaeologist/cache/`，同一 commit 重复分析秒出结果且零 API 消耗。

### API 消耗预估

对一个 50 个 `.py` 文件的中型仓库：Phase 2.5 规划 1 次 + Phase 3 每批 1-3 轮（约 5-8 个批次）+ Phase 3.5 一致性 1 次 + Phase 4 综合 1 次，总计约 **8-12 次 API 调用**，成本控制在 ¥0.1 以内。

---

## 技术栈与依赖

### 运行时依赖

| 类别 | 依赖 | 版本要求 | 用途 |
|------|------|---------|------|
| **LLM** | Hy3 API | — | 全系统推理引擎 |
| **Python** | Python | `>= 3.10` | 后端运行时 |
| **Node.js** | Node.js | `>= 18` | 前端运行时 |
| **Web 框架** | FastAPI | `>= 0.115.0` | 后端 API 服务 |
| **ASGI 服务器** | Uvicorn | `>= 0.30.0` | 生产级 ASGI 服务 |
| **Git 操作** | GitPython | `>= 3.1.0` | 仓库 clone 与操作 |
| **图计算** | NetworkX | `>= 3.3` | 依赖图构建 + PageRank |
| **向量检索** | ChromaDB | `>= 0.5.0` | 追问阶段语义搜索 |
| **嵌入模型** | sentence-transformers | `>= 3.0.0` | BGE-M3 文本向量化 |
| **数据校验** | Pydantic | `>= 2.0` | 全系统数据模型 |
| **配置管理** | pydantic-settings | `>= 2.0` | 环境变量管理 |
| **HTTP 客户端** | httpx | `>= 0.27.0` | Hy3 API 调用 |
| **Hy3 SDK** | openai | `>= 1.50.0` | 兼容 OpenAI SDK 调用 Hy3 |
| **MCP** | mcp | `>= 1.0.0` | 外部工具协议 |
| **CLI** | click + rich | `>= 8.1.0` | 命令行入口 + 美化输出 |
| **前端框架** | React | `^19.0.0` | Web UI |
| **CSS** | Tailwind CSS | `^3.4.14` | 样式系统 |
| **图可视化** | D3.js | `7.9.0` | 力导向依赖图 |
| **架构图** | Mermaid | `11.15.0` | 架构全景图渲染 |
| **构建工具** | Vite | `^6.0.0` | 前端打包 |

### 开发依赖

| 依赖 | 用途 |
|------|------|
| pytest + pytest-asyncio | 单元测试与异步测试 |
| ruff | Python 代码格式化与 lint |
| mypy | 静态类型检查 |
| TypeScript | 前端类型系统 |

### 系统依赖

* **git** — 命令行可用（用于 clone 仓库）
* **macOS / Linux / WSL** — 已验证 macOS（需设置 `GIT_HTTP_VERSION=1.1` 解决 libcurl HTTP/2 兼容性问题）

---

## 快速开始

### 1. 环境准备

* Python 3.10+
* Node.js 18+
* git 命令行
* Hy3 API Key — 从 [TokenHub](https://tokenhub.tencentmaas.com) 获取

### 2. 安装

```bash
# 克隆项目
git clone https://github.com/<你的用户名>/codebase-archaeologist.git
cd codebase-archaeologist

# 安装 Python 依赖
pip install -e . --break-system-packages

# 安装前端依赖
cd frontend && npm install && cd ..
```

> ⚠️ **必须配置 Hy3 API Key 才能运行！** 本项目不包含任何 API Key，你需要在启动前自行配置。详见下方 **[3. 配置 API Key](#3-配置-api-key)**。

### 3. 配置 API Key

> 🔑 本项目已提交的 `backend/.env` 中 **API Key 为空**，必须填入你自己的 Key 才能调用 Hy3。

```bash
# 从 TokenHub 获取 Hy3 API Key：https://tokenhub.tencentmaas.com
# 打开 backend/.env，将 ARCHAEOLOGIST_HY3_API_KEY 设为你的 Key：

ARCHAEOLOGIST_HY3_API_KEY=你的Key填在这里
```

验证配置是否生效：

```bash
python scripts/verify_hy3.py
```

### 4. 启动

### 3. 启动

**方式 1：Web UI（推荐）**

```bash
# 终端 1 — 后端
cd backend
uvicorn app.main:app --reload --port 8000

# 终端 2 — 前端
cd frontend
npm run dev

# 浏览器打开 http://localhost:5173
```

**方式 2：CLI**

```bash
# 分析仓库并输出报告
archaeologist analyze https://github.com/user/repo --verbose -o report.json

# 启动 Web 服务
archaeologist serve
```

### 5. 验证

```bash
python scripts/verify_hy3.py
```

---

## 部署方案

### 本地开发（当前方案）

开发阶段直接双终端运行，Vite 自动代理 `/api` 请求到后端。适合调试和快速迭代。

### 生产部署

后端使用 Gunicorn + Uvicorn workers（4 worker 推荐），前端 `npm run build` 后即可通过 Nginx 反向代理。

```bash
# 后端
gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend.app.main:app --bind 0.0.0.0:8000

# 前端构建
cd frontend && npm run build
# 将 dist/ 部署到 Nginx /usr/share/nginx/html，API 请求反向代理到 localhost:8000
```

---

## 两个端到端 Demo

### Demo 1：已分析仓库的闪电回访（~30 秒）

[![Demo 1 封面](https://bobvictory.github.io/codebase-archaeologist/demo1-poster.png)](https://bobvictory.github.io/codebase-archaeologist/demo1.mp4)

**场景**：你之前已经分析过一个仓库，隔了几天有人问你"这个项目有哪些风险点？各模块之间怎么依赖的？"——你不想再看一遍代码，也不想再花几分钟重新跑一次分析。

**流程**：

1. 在 Web UI 中再次粘贴同一个仓库 URL，点击"开始分析"
2. 命中缓存，直接从 `~/.archaeologist/cache/` 读取已存储的 `ArchitectureReport`（秒出，零 API 消耗）
3. 前端立即展示完整报告：架构摘要、D3 依赖关系图、Mermaid 架构图、模块详情、调用链追踪、风险清单
4. 在追问 Tab 中用 Hy3 流式追问任意细节，Prompt Cache 将成本降低约 75%

### Demo 2：陌生仓库深度考古（~2 分钟）

[![Demo 2 封面](https://bobvictory.github.io/codebase-archaeologist/demo2-poster.png)](https://bobvictory.github.io/codebase-archaeologist/demo2.mp4)

**场景**：收到一个从未见过的 GitHub 仓库链接，明天就要开始贡献代码，但完全没有头绪。

**流程**：

1. 在 Web UI 中粘贴仓库 URL，点击"开始分析"
2. 后端自动 clone → 本地 AST 构建精确依赖图 + PageRank
3. **Hy3 Planner** 制定分批策略：从依赖图和 PageRank 中推理出最优批次划分
4. **Hy3 ReAct Agent** 逐批分析代码——每批次模型自主调用 grep_search / file_read / ast_parse / dep_graph_query 进行跨文件调查
5. **Hy3 Consistency Check** 全量跨批次交叉验证，消除矛盾
6. **Hy3 Synthesizer** 综合研判，以严格 JSON Schema 输出结构化架构报告
7. 前端展示完整报告，同时持久化到缓存中

---

## CodeBuddy 协作记录

本项目由人工主导设计 + CodeBuddy 辅助实现。核心算法和架构由人工完成，CodeBuddy 主要在以下方面提供了效率提升：

| 模块 | 协作方式 | CodeBuddy 贡献 |
|------|---------|---------------|
| **前端 UI 全部组件** | 人工给出设计要求，CodeBuddy 生成初始代码，人工调优交互 | ~70% |
| (UrlInput / ProgressPanel / ReportTabs / OverviewTab / ModulesTab / DepGraphTab / ArchitectureDiagramTab / CallChainsTab / RisksTab / DeployGuideTab / QATab) | | |
| **FastAPI 路由骨架** | 人工设计 API 契约，CodeBuddy 完成端点模板 | ~40% |
| **工具 Schema 生成** | 人工定义接口语义，CodeBuddy 生成 JSON Schema | ~60% |
| **CLI 格式化输出** | CodeBuddy 生成 Rich 表格渲染代码 | ~80% |
| **Prompt 中文润色** | 人工设计分析维度，CodeBuddy 润色中文措辞 | ~30% |
| **向量存储封装** | 人工设计检索策略，CodeBuddy 生成 ChromaDB 调用 | ~50% |
| **CSS 主题切换** | 人工指定色板，CodeBuddy 批量修改所有组件 | ~80% |
| **Agent 核心循环** | 人工设计 + 人工实现 | 0% |
| **依赖图算法** | 人工设计 PageRank + 循环检测 + 依赖解析 | 0% |
| **缓存系统** | 人工设计 commit-hash 键值 + 持久化策略 | ~10% |

---

## 项目结构

```
codebase-archaeologist/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── hy3_client.py          # Hy3 API 封装（Planner/Reader/Agent/Synthesizer 四种模式）
│   │   │   ├── cache.py               # Commit 级别分析结果缓存
│   │   │   ├── job_manager.py         # 任务状态管理 + SSE 实时推送
│   │   │   └── vector_store.py        # ChromaDB 持久化语义检索
│   │   ├── pipeline/
│   │   │   ├── orchestrator.py        # 六阶段分析管线核心引擎
│   │   │   └── prompts.py             # Hy3 Prompt 模板（Planner/Reader/Consistency/Synthesizer/QA）
│   │   ├── tools/
│   │   │   ├── registry.py            # 工具注册 + MCP 调度
│   │   │   └── internal_tools.py      # 内部工具实现（git_clone/file_read/grep/ast_parse/dep_graph）
│   │   ├── mcp/
│   │   │   └── server.py              # MCP Server（web_search + code_exec）
│   │   ├── models.py                  # Pydantic 全系统数据模型（17 个模型类）
│   │   ├── config.py                  # pydantic-settings 配置管理
│   │   ├── main.py                    # FastAPI 应用（8 个 REST 端点 + SSE）
│   │   └── cli.py                     # Click + Rich CLI 入口
│   ├── tests/
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── UrlInput.tsx            # URL 输入组件
│   │   │   ├── ProgressPanel.tsx       # 实时进度 SSE 面板
│   │   │   ├── ReportTabs.tsx          # 报告多 Tab 容器
│   │   │   └── tabs/
│   │   │       ├── OverviewTab.tsx      # 架构摘要 + Token 用量
│   │   │       ├── ModulesTab.tsx       # 模块搜索 + 展开详情
│   │   │       ├── DepGraphTab.tsx      # D3 力导向依赖图（箭头 + 拖拽 + 高亮）
│   │   │       ├── ArchitectureDiagramTab.tsx  # Mermaid 架构分层全景图
│   │   │       ├── CallChainsTab.tsx    # 调用链可视化
│   │   │       ├── RisksTab.tsx         # 风险分级筛选 + 修复建议
│   │   │       ├── DeployGuideTab.tsx   # 自动生成的部署指南
│   │   │       └── QATab.tsx            # 追问对话界面
│   │   ├── api.ts                      # API 客户端 + SSE fallback 轮询
│   │   ├── types.ts                    # TypeScript 类型定义（与 Pydantic 模型对齐）
│   │   └── App.tsx                     # 主应用组件
│   ├── index.html
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── package.json
├── scripts/
│   └── verify_hy3.py                   # Hy3 API 连通性验证脚本
├── pyproject.toml                      # Python 项目定义 + 依赖
├── .editorconfig
├── .gitignore
├── .env.example
└── README.md
```

---

## License

Apache License 2.0

---

<p align="center">
  <sub>Built with ❤️ for the Hy3 Rhinobird 2026 Hackathon</sub>
</p>
