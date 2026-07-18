# CODEBUDDY.md — Hy3 RAG 项目笔记

> 面向 AI 协作助手的项目说明。描述结构、运行方式、关键约定与常见陷阱。

## 项目定位
基于腾讯混元 Hy3 大模型的多文档 RAG 问答 Web 应用。
- API：`https://tokenhub.tencentmaas.com/v1`（OpenAI 兼容），模型 `hy3`。
- 推理模式通过 `extra_body={"reasoning_effort": "low"}` 控制（见 `hy3_client.py`）。

## 运行
```bash
.venv/Scripts/python.exe run.py
# 或手动（注意：backend/ 下是扁平导入，必须 cd 到 backend/ 再启动，且用 main:app 而非 backend.main:app）
cd backend && ..\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8766
```
前端为纯静态 `frontend/index.html`，由 FastAPI 在 `/` 托管；静态资源挂在 `/static`（`/static/app.js`、`/static/styles.css`），改完前端需刷新并忽略缓存（URL 带 `?v=6` 版本号）。

## 依赖约束（重要）
- **嵌入模型**：`paraphrase-multilingual-MiniLM-L12-v2`，用 **ONNX Runtime + tokenizers** 推理，
  **禁止使用 sentence-transformers / torch**（Windows 沙箱内安装会失败）。
- `backend/embedder.py` 的 `create_embedder()` 优先加载 ONNX，失败时回退 `MockEmbedder`（哈希向量，仅供离线兜底测试）。
- `chromadb` 使用 `PersistentClient(path=...)`，collection 通过 `_LocalEmbeddingFunction` 接入本地嵌入。
- `data/` 全部为运行时数据，**不入库**（`.gitignore` 已排除）。`.env` 含密钥，禁止提交。

## 关键模块
- `config.py`：所有路径 / 参数集中于此；`HF_ENDPOINT` 默认 `https://hf-mirror.com`。
- `vector_store.py`：`_LocalEmbeddingFunction` 必须是**模块级类**（否则 ChromaDB 持久化 pickle 反序列化失败）。
- `memory_manager.py`：模块级单例 `doc_memory` / `folder_manager` / `conversation_memory`。
  `DocumentMemory` 提供 `set_folder`，并支持与 vector store 双向同步。
- `rag_engine.py`：`answer_stream()` 异步生成器，产出 `context` / `token` / `done` / `error` 事件。

## 常见陷阱
- 勿将 `hy3-rag` 目录与腾讯 Hy3 **模型仓库**混淆——两者不可混放。本目录只放 RAG 应用源码。
- 提交到 GitHub 时务必 `.gitignore` 排除 `.env`、`data/`、`*.pyc`、`__pycache__`。
- 前端版本号改动需同步 `index.html` 中 `app.js?/styles.css?` 的 `?v=` 查询参数以破除缓存。
- **PDF 解析**：`_read_pdf` 必须用 **pypdf** 为主解析器；pdfplumber 仅作兜底（pypdf 提取 <50 字符时才用）。
  原因：pdfplumber 在部分 PDF（实测 `考点汇总.pdf`）上会**原生段错误（segfault，无 Python traceback，直接崩进程）**，不能作为主解析器。
- **Git 仓库历史**：`hy3-rag/.git` 历史上曾被腾讯模型仓库覆盖，`rhinobird2026` 分支已重置为 **orphan（无模型仓库历史）**，仅含 RAG 源码。
  提交前确认 `git status -sb` 显示 `## rhinobird2026`（**无 upstream**）；若显示跟踪 `upstream/rhinobird2026` 说明被模型仓库配置污染，需 `git branch --unset-upstream` 防止误推到模型仓库。
