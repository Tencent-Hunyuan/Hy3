# hy3-research

> 深度研究助手 — 输入一个主题，自动完成 Plan → Search → Fetch → Synthesize → Report 全流程，**由 Hy3 大模型驱动**。

零外部依赖（仅 Python 标准库 + 少量 pip 包），支持 OpenAI 兼容的 Hy3 API，内置 **mock 离线模式**，开箱即可演示。

---

## ✨ 它能做什么

- **自动研究规划**：给定一个主题，Hy3 自动拆分为 3-6 个子主题，生成搜索策略和报告大纲。
- **并行搜索抓取**：Tavily + DuckDuckGo 双引擎搜索，并行抓取源内容。
- **结构化综合**：每个子主题独立综合，保留引用标注 [1][2]。
- **长文报告生成**：一键生成带摘要、正文、结论、引用列表的完整 Markdown 报告。
- **Web 交互查看**：内置 HTTP 服务器，浏览器查看报告（暗色/亮色主题、引用 tooltip）。
- **交互 + 自动双模式**：CLI 分步交互确认，或 `--auto` 一键到底。

---

## 🧩 Hy3 在系统中承担的角色

本应用**全程通过 Hy3 的 HTTP API 调用模型**，没有任何训练 / 微调 / 本地推理部署。

```
用户输入研究主题
     │
     ▼
hy3research CLI
     │  构造 system prompt + 用户输入
     ▼
Hy3 /chat/completions  ──►  研究计划 (JSON)
     │                     子主题综合 (per subtopic)
     │                     最终报告 (Markdown)
     ▼
本地代码 (搜索 + 抓取 + 编排 + 渲染)
```

- **Hy3 负责「理解 + 生成 + 综合」**：拆分研究计划、综合多源材料、撰写结构化报告。
- **本地代码负责「搜索 + 编排 + 渲染」**：Tavily/DDG 搜索、URL 抓取、并行调度、Web 报告展示。

> 即使在无 key 的 **mock 模式**下，整体交互链路也完全可跑通，便于离线开发与评审。

---

## 🚀 快速开始

### 1. 准备

```bash
# 需要 Python 3.8+
python3 --version

# 安装依赖
pip install -r requirements.txt

# 复制并填写 Hy3 接入信息
cp .env.example .env
# 编辑 .env：填入 HY3_API_KEY / HY3_BASE_URL / HY3_MODEL
# 可选填入 TAVILY_API_KEY（不填则自动使用 DuckDuckGo 搜索）
```

> 不填 `HY3_API_KEY` 会自动进入 mock 模式，可直接体验交互。

### 2. 运行

```bash
# 交互模式（每阶段确认）
python -m hy3research "量子计算在药物研发中的应用"

# 自动模式（全流程无干预）
python -m hy3research --auto "AI芯片发展趋势"

# Mock 模式（离线演示）
python -m hy3research --mock "测试主题"

# 仅生成研究计划
python -m hy3research --plan-only "主题"

# 指定输出目录
python -m hy3research --output ./my-research "主题"

# 完成后自动启动 Web 服务
python -m hy3research --auto --serve "主题"
```

### 3. 查看报告

```bash
# 启动 Web 服务
python -m hy3research serve outputs/<报告目录>/

# 或直接浏览器打开
open outputs/<报告目录>/report.html
```

---

## 🎬 两个端到端 Demo 流程

> 录制脚本见 `demo/record.sh`。

**Demo 1 — 浅度研究 (预计 60-90s)**

```
$ python -m hy3research --auto "Kubernetes vs Serverless 2026年企业选型对比"
→ Plan: 3 subtopics (成本对比、性能对比、生态对比)
→ Search: ~20 sources → Fetch: ~10 URLs
→ Synthesize: 3 concurrent Hy3 calls
→ Report: 完整 Markdown + Web 页面
```

**Demo 2 — 深度研究 (预计 90-120s)**

```
$ python -m hy3research --auto "Transformer架构的替代方案最新进展"
→ Plan: 5 subtopics (Mamba、RWKV、RetNet、线性注意力、混合架构)
→ Search: ~30 sources → Fetch: ~15 URLs
→ Synthesize: 5 concurrent Hy3 calls
→ Report: 深度综述 + 引用索引 + Web 页面
```

---

## 🤝 与 CodeBuddy / WorkBuddy 的协作记录

本仓库为「vibe-coded」作品，下列模块由 **CodeBuddy / WorkBuddy（基于 Hy3）** 协助生成或重构：

- `hy3research/client.py`：Hy3 OpenAI 兼容客户端、重试逻辑与 mock 模式（由 CodeBuddy 生成骨架，WorkBuddy 补充推理模型兼容处理）。
- `hy3research/planner.py`：研究计划生成、JSON 解析与容错（由 WorkBuddy 设计 prompt 结构）。
- `hy3research/searcher.py`：Tavily + DDG 双引擎搜索与并行调度（复用 issue3 已验证逻辑，WorkBuddy 适配）。
- `hy3research/reporter.py`：长文报告生成 prompt 设计与输出保存（由 WorkBuddy 撰写）。
- `hy3research/__main__.py`：CLI 编排逻辑与交互流程（由 WorkBuddy 搭建骨架）。
- `templates/report.html`：Web 报告模板（由 WorkBuddy 设计并实现暗色/亮色主题）。
- `README.md` 与 `demo/` 目录：由 WorkBuddy 撰写。

其余配置、测试与调试由作者完成。

---

## 📦 项目结构

```
hy3-research/
├── hy3research/
│   ├── __init__.py          # 版本信息
│   ├── __main__.py          # CLI 入口 (argparse)
│   ├── config.py            # 配置 / .env 加载
│   ├── client.py            # Hy3 客户端 (OpenAI 兼容 + mock)
│   ├── planner.py           # 研究计划生成 (Hy3)
│   ├── searcher.py          # Tavily + DDG 后备搜索
│   ├── fetcher.py           # URL 内容抓取 + 文本提取
│   ├── synthesizer.py       # 源材料 → Hy3 综合 (per subtopic)
│   ├── reporter.py          # 长文报告 + 引用生成 (Hy3)
│   ├── server.py            # HTTP 静态文件服务
│   └── ui.py                # 终端渲染
├── templates/
│   └── report.html          # 报告 Web 模板 (marked.js CDN)
├── tests/                   # 单元测试
├── demo/                    # 演示录制脚本
├── outputs/                 # 默认报告输出目录
├── .env.example
└── README.md
```

---

## 🔒 安全说明

- API Key 仅通过环境变量 / `.env` 提供，且 `.env` 已被 git 忽略，不会入库。
- 仅在用户确认后执行网络搜索和内容抓取（交互模式）。
- Mock 模式不发起任何网络请求。

---

## 📄 License

MIT — 详见 [LICENSE](../LICENSE)。

---

## 🐦 提交说明（rhinobird2026）

本应用在 `issue4/` 目录开发，向 `Tencent-Hunyuan/Hy3` 的 `rhinobird2026` 分支提交 PR。
PR 附有：项目说明（即本 README）+ 两个 demo 的视频/GIF。
