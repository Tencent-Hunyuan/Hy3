# [Hy3 RAG] 多文档检索增强问答应用（Powered by Hy3）

> 本应用为**独立应用仓库**，代码见 Fork：https://github.com/northernmountai8n/Hy3
> （基于活动分支 `rhinobird2026` 开发，按 issue 要求在此补充项目说明与仓库链接）

## 应用简介
基于腾讯混元 **Hy3** 的多文档 RAG（检索增强生成）问答 Web 应用。用户上传本地文档
（PDF / Word / Markdown / 代码 / 数据等 14 种格式），系统向量化后通过"检索 + 大模型生成"
对文档内容提问，返回**带引用来源**的流式回答。适用于论文精读、法规/技术手册查询、
课程资料答疑等场景。

## Hy3 在系统中的角色
- Hy3 是本应用**唯一的大模型推理来源**，全程通过 OpenAI 兼容 API
 （`https://tokenhub.tencentmaas.com/v1`，模型 `hy3`）调用，**不做训练 / 微调 / 本地推理部署**。
- 承担 RAG 流水线第 4 步的**回答生成**：检索上下文 → 拼接系统提示词 → Hy3 流式生成带引用回答（SSE 逐字输出）。
- 文档嵌入使用本地 ONNX 多语言模型（`paraphrase-multilingual-MiniLM-L12-v2`），**不经过 Hy3**，
  满足活动"全程 API 调用 Hy3"的约束。

## 核心特性
- 多格式文档导入（14 种）、本地多语言嵌入（ONNX Runtime，无需 torch）
- ChromaDB 持久化向量检索（余弦相似度，支持按文档 / 文件夹 / 指定来源过滤）
- 文档记忆持久化、文件夹分类管理、多轮对话记忆（保存/恢复）
- 流式回答 + 引用来源展示；纯前端单页应用（上传 / 检索 / 记忆）

## 端到端 Demo（≤2min）
1. **上传 → 检索 → 问答**：`demo/demo1-upload-qa.mp4`
2. **文件夹限定 + 多轮记忆**：`demo/demo2-folder-memory.mp4`

## CodeBuddy / WorkBuddy 协作说明
- 后端全部模块由 CodeBuddy 基于需求协作重建与联调；前端由 WorkBuddy 从零生成；
  关键修复（ChromaDB 1.5.9 接口适配、pdfplumber 段错误规避、静态资源挂载）由 AI 协作定位修复。
- 详见仓库 [CODEBUDDY.md](./CODEBUDDY.md) 与 [README.md](./README.md)。

## 运行方式
```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
cp .env.example .env   # 填入 HY3_API_KEY
.venv/Scripts/python.exe run.py   # 打开 http://127.0.0.1:8766
```
