# Hy3 Research Studio

> AI 原生科研与创作工作台 → Powered by [Tencent Hy3](https://github.com/Tencent-Hunyuan/Hy3)

**独立仓库地址**：[https://github.com/Xtdzs/Hy3-Research-Studio](https://github.com/Xtdzs/Hy3-Research-Studio)

---

## 项目简介

Hy3 Research Studio 是一款面向科研人员的 AI 原生全流程科研工作台，基于腾讯混元 Hy3 模型的强 Agent 能力（Function Calling + SSE 流式输出 + 推理模式切换），覆盖从**灵感激发 → 文献检索 → 论文研读 → 深度研究 → 学术写作 → 功能创造**的完整科研链路。

本项目为腾讯犀牛鸟开源人才培养计划参赛作品，使用 CodeBuddy + Hy3 API vibe-coded 开发完成。

---

## 核心功能模块（11 个模块）

| 模块 | 说明 | Hy3 能力体现 |
|------|------|-------------|
| 🔬 **深度研究（Deep Research）** | 8阶段自动化研究流水线：规划→检索→压缩→假设→证据图谱→研究空白→实验设计→报告，SSE实时进度，流式带 [sN] 引用的学术报告 | 长链 Agent 编排、tool_choice 强制检索、流式推理输出 |
| 🔍 **智能检索（Smart Search）** | 跨 OpenAlex/Crossref/arXiv 并行学术检索，Hy3 自动优化检索式（中文→英文），LLM 语义过滤 | Function Calling 多源并行检索、查询优化 |
| 💡 **思路提炼（Idea Refiner）** | Agent 模式科研教练对话，强制"先检索再回答"，Hy3 自动生成2-4个后续选择按钮，多轮收敛 | tool_choice 强制调用、动态 follow-up 按钮生成 |
| 📄 **论文研讨（Paper Seminar）** | PDF 解析上传，基于全文内容的多轮对话（总结贡献/分析局限/提取大纲） | 长文档理解、多轮上下文追踪 |
| ✍️ **写作助手（Writing Studio）** | 4种写作工具：摘要生成/大纲生成/段落扩写/文献综述，流式输出 | 结构化写作、流式生成 |
| 🔨 **创造工坊（Feature Workshop）** | ⚠️ 概念验证（PoC）：功能市场+AI一句话创建自定义科研工具（名称/emoji/prompt/布局自动生成） | 动态 Prompt 生成、零代码工具创建 |
| 📚 **我的文库** | 跨模块论文收藏、文件夹组织、笔记、跨会话持久化 | - |
| 📊 **反馈看板** | 提交反馈、词云可视化、投票排序 | - |
| 🕐 **历史动态** | 跨模块统一活动日志、模块筛选、一键继续上次任务 | - |
| 👤 **个人主页** | 身份/机构/研究兴趣设置、个性化推荐 | 个性化推荐 |
| ⚙️ **设置** | API Key 管理、检索源开关、偏好设置、数据管理 | - |

---

## 技术栈

| 层级 | 技术选型 |
|------|---------|
| 后端 | Python 3.10+ / FastAPI / SSE / Pydantic |
| 前端 | 零构建 SPA（原生 HTML + CSS + JS） |
| AI 模型 | 腾讯混元 Hy3（OpenAI 兼容接口） |
| 学术数据源 | OpenAlex / Crossref / arXiv |
| 数据持久化 | JSON 文件存储 |
| 部署 | 一键启动 `python run.py` |

---

## 为什么选择 Hy3

Hy3 在本项目中承担核心推理和 Agent 编排角色：

1. **Function Calling 稳定性**：深度研究流水线中，Hy3 可靠地在 8 个阶段间切换工具调用，tool_choice 精确控制检索行为
2. **流式输出 + SSE**：所有生成内容均采用流式输出，配合 SSE 实时进度条，提供类 ChatGPT 的交互体验
3. **推理模式切换**：简单问答用 `no_think` 快速响应，深度研究用 `high` 模式完整推理链
4. **长上下文理解**：论文研讨中，Hy3 能基于上传的完整 PDF 内容进行多轮深入对话
5. **中文原生优化**：中文学术场景下的检索式优化、报告生成、思路提炼表现优异

---

## 快速开始

```bash
git clone https://github.com/Xtdzs/Hy3-Research-Studio.git
cd Hy3-Research-Studio
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填入 HY3_API_KEY
python run.py
```

浏览器打开 http://localhost:8000 即可使用。

---

## 功能演示

项目 README 中包含 6 段内嵌演示视频（直接在 GitHub 页面播放），覆盖全部 11 个功能模块，总时长约 12 分钟。

▶️ [点击查看 README 中的演示视频](https://github.com/Xtdzs/Hy3-Research-Studio#-demo-videos)

---

## 项目亮点

- **全链路覆盖**：从灵感到报告的完整科研工作流，而非单点工具
- **深度 Agent 编排**：8阶段深度研究流水线体现 Hy3 强 Agent 能力
- **零构建前端**：纯原生 SPA，无需 Node.js 构建工具链，部署极简
- **开箱即用**：7个 Python 依赖，一条命令启动
- **离线 Demo 模式**：无需 API Key 即可体验 UI 交互流程
- **中英文双语 README**：面向国际开源社区

---

## 项目结构

```
Hy3-Research-Studio/
├── backend/              # FastAPI 后端（40+ API 端点）
│   ├── main.py           # SSE + REST 路由入口
│   ├── pipeline.py       # 深度研究 8 阶段流水线
│   ├── hy3_client.py     # Hy3 客户端封装（stream/JSON/tool_calls）
│   ├── search.py         # OpenAlex/Crossref/arXiv 多源检索
│   ├── features.py       # 创造工坊数据层
│   └── prompts.py        # 30+ Prompt 模板
├── frontend/             # 零构建 SPA
│   ├── index.html        # 所有视图
│   ├── app.js            # 路由/SSE/工作区管理
│   └── styles.css        # 深色主题
├── data/                 # JSON 持久化（自动生成）
├── docs/                 # 技术报告与产品方案
├── tests/                # 单元测试与评测框架
└── run.py                # 一键启动
```

---

## 已知限制与未来工作

- ⚠️ **创造工坊**为概念验证（PoC），布局引擎和 Prompt 编排有待优化
- PDF 解析目前支持文本型 PDF，扫描版需 OCR 预处理
- 文库的笔记功能为基础实现，未来计划增加知识图谱关联
- 计划接入更多学术数据源（Semantic Scholar、PubMed 等）

---

## License

MIT License
