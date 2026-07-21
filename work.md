# HyGraph · 由 Hy3 驱动的知识图谱 / 思维导图生成器

> 把任意非结构化文本或主题，一键转化为可交互的知识图谱 / 思维导图。

## Hy3 在系统中承担的角色

Hy3 是本系统唯一的智能内核，所有「从文本到结构」的智力工作都由 Hy3 完成：

1. **结构化抽取**：接收原始文本 / 主题，输出规范的图谱 JSON（nodes + edges）
2. **两种模式**：思维导图（层级主题树）/ 知识图谱（实体 + 语义关系）
3. **抗幻觉 / 可溯源**：每个节点附 `source` 原文片段，缺失标注「待验证」
4. **多轮追问**：用户可基于图谱上下文追问，Hy3 流式回答

Hy3 通过 OpenAI 兼容 `chat.completions` 协议接入，`reasoning_effort` 设 `low`（结构化抽取）/ `no_think`（流式问答）。

## 快速开始

### 后端

```bash
cd server
cp .env.example .env
# 编辑 .env，填入 Hy3 API 配置
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd web
npm install
npm run dev
# 访问 http://localhost:5173
```

## 环境变量

| 变量 | 说明 | 示例 |
|---|---|---|
| `HY3_API_KEY` | Hy3 API 密钥 | `sk-xxx` |
| `HY3_BASE_URL` | Hy3 端点（OpenAI 兼容） | `https://api.hy3.com/v1` |
| `HY3_MODEL` | 模型名 | `hy3` |
| `DB_PATH` | SQLite 数据库路径 | `data/hygraph.db` |

## 技术栈

- **前端**：React 18 + TypeScript + Vite + AntV G6 v5 + Zustand + Tailwind CSS + react-markdown
- **后端**：Python 3.11 + FastAPI + LangChain + langchain-openai + SQLite + uv

## 使用流程

1. 左侧「新建会话」
2. 中间输入文本，选择模式（思维导图 / 知识图谱），点击发送
3. 右侧自动渲染交互式图谱
4. 点击节点查看详情，可追问展开

## Hy3 协作记录
代码由workbuddy/ with + hy3生成
