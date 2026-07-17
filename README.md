# Hy3 RAG — 多文档检索增强问答应用

基于 **Hy3**（腾讯混元 295B MoE 大模型）的多文档 RAG（检索增强生成）问答系统。
支持将本地文档（PDF / Word / Markdown / 代码 / 数据等 14 种格式）导入知识库，
通过向量检索 + 大模型生成，对文档内容提问并获取带引用的回答。

> 本项目为「犀牛鸟 2026」端到端应用赛题的提交作品。

---

## ✨ 核心特性

- **多格式文档导入**：PDF、DOCX、MD、TXT、Python、JSON、CSV、XML、HTML 等 14 种格式。
- **本地多语言嵌入**：使用 `paraphrase-multilingual-MiniLM-L12-v2`（384 维，ONNX Runtime 推理），
  无需 `torch` / `sentence-transformers`，支持中英及 50+ 语言，离线可用（首次需下载模型权重）。
- **向量检索**：ChromaDB 持久化存储，余弦相似度，可按文档 / 文件夹 / 指定来源过滤检索范围。
- **文档记忆持久化**：文档元数据与文件夹归类长期保存，重启不丢失。
- **文件夹分类管理**：将文档归入不同文件夹，按文件夹限定问答范围。
- **对话记忆**：支持多轮对话、历史会话保存与恢复。
- **流式回答**：基于 SSE 的逐字流式输出，带「引用来源」展示。
- **拖拽限定范围**：可将侧边栏文档拖入输入框，仅基于该文档作答。

---

## 📁 项目结构

```
hy3-rag/
├── backend/
│   ├── config.py            # 配置（API、路径、分块、检索参数）
│   ├── hy3_client.py        # Hy3 OpenAI 兼容客户端（含流式）
│   ├── document_parser.py   # 14 种文档格式解析
│   ├── text_chunker.py      # 递归分块 + 重叠合并
│   ├── embedder.py          # 本地 ONNX 多语言嵌入（含 Mock 兜底）
│   ├── vector_store.py      # ChromaDB 封装 + 本地嵌入函数
│   ├── rag_engine.py        # RAG 检索→生成流水线（异步流式）
│   ├── memory_manager.py    # 文档记忆 / 文件夹 / 会话记忆
│   └── main.py              # FastAPI 服务与所有 API 路由
├── frontend/
│   ├── index.html           # 单页应用（侧边栏 + 对话区）
│   ├── styles.css           # 样式
│   └── app.js               # 前端逻辑（上传 / 检索 / SSE / 记忆）
├── data/                    # 运行时数据（已 gitignore，不入库）
│   ├── uploads/             # 用户上传的文档
│   ├── chroma_db/           # ChromaDB 向量库
│   └── memory/             # 文档记忆 / 文件夹 / 会话 JSON
├── run.py                   # 启动器（释放端口 + 启动服务 + 打开浏览器）
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 快速开始

### 1. 准备环境

需要 Python 3.10+。建议使用虚拟环境：

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows
# source .venv/bin/activate   # Linux / macOS
pip install -r requirements.txt
```

### 2. 配置 API Key

复制 `.env.example` 为 `.env` 并填入你的 Hy3 API Key：

```bash
cp .env.example .env
# 编辑 .env，设置 HY3_API_KEY=你的密钥
```

### 3. 启动

```bash
python run.py
```

服务默认运行在 `http://localhost:8766`，启动后会自动打开浏览器。
也可直接使用 uvicorn：

```bash
.venv/Scripts/python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8766
```

---

## 🔌 API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/api/health` | 健康检查 |
| GET  | `/api/documents/stats` | 文档统计 |
| POST | `/api/documents/upload` | 上传文档（multipart） |
| GET  | `/api/documents?folder_id=` | 文档列表（可按文件夹过滤） |
| DELETE | `/api/documents/{filename}` | 删除文档 |
| POST | `/api/qa/stream` | 流式问答（SSE） |
| POST | `/api/qa/chat` | 非流式问答 |
| GET/POST/DELETE | `/api/folders` | 文件夹管理 |
| GET/POST/DELETE | `/api/conversations` | 会话管理 |

问答请求体（`/api/qa/chat`）示例：

```json
{
  "question": "这篇论文的主要贡献是什么？",
  "top_k": 6,
  "conversation_id": "可选",
  "folder_id": "可选，仅检索该文件夹文档",
  "source_filters": ["可选，仅检索指定文档名"]
}
```

---

## 🧠 工作原理

1. **导入**：文档解析为纯文本，按 `CHUNK_SIZE=800` / `CHUNK_OVERLAP=150` 递归分块。
2. **嵌入**：每块经本地 ONNX 多语言模型编码为 384 维向量，L2 归一化。
3. **检索**：问题向量在 ChromaDB 中做余弦相似度近邻搜索，取 `TOP_K=6` 个高相关块。
4. **生成**：将检索到的上下文拼接进系统提示词，调用 Hy3 流式生成回答，并回传引用来源。

---

## 📝 许可

[MIT License](./LICENSE)
