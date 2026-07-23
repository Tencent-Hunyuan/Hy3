# HyGraph · 通用文档知识问答系统

上传任意文档（扫描件 / 文本 PDF、Word、PPT、Excel、EPUB、Markdown、TXT），系统在本地转写并轻结构化为「知识页」；提问时按导航优先召回命中整页原文，喂给大模型只读作答并标注文件名 + 页码 + 原文片段。

**核心特性**：文档与会话解耦可跨会话复用；扫描件本地 OCR（Apple Silicon 用 MPS 加速）；回答带页码溯源，支持展开查看命中原文；支持接入多个 LLM provider（Hy3 / OpenRouter / Ollama）。


---

## Hy3 在系统中的角色

Hy3 是系统的默认且主用 LLM，全程通过 OpenAI 兼容 API 调用，承担查询期的全部语言理解与生成任务。系统的设计主线是「小模型也能高质量回答」——把最难的文档理解与结构化放到入库期一次做好（本地转写 / 章节切分 / 知识页编译 / 向量化，均零 token、不经 LLM），查询期让 Hy3 只做有界任务：

- **只读作答**：召回命中的知识页整页原文注入后，Hy3 只读、只引用、组织语言，逐句标注文件名 + 页码，不使用外部知识、不编造。
- **意图路由**：规则优先判定知识型 / 闲聊，不确定时用 `no_think` 档位轻量二分类；闲聊路径跳过检索直接作答。
- **召回质量评估**：规则判定为主，中度以上推理档位可选 Hy3 做 yes/no 有界判断。
- **Query 改写**：召回不合格时用低推理档位改写查询并重召回（硬上限 1 次）。
- **深度思考分档**：通过 `reasoning_effort` 多档切换，简单问题直出省 token，复杂问题做多步思考。
- **会话标题生成**：根据首轮问答用低推理档位生成简洁标题。

一句话：**Hy3 是查询期的"读者与作者"，而非"研究员"**——理解与合成的重活在入库期完成，Hy3 负责在有界上下文里做高质量、可溯源的语言组织与推理。

---

## 环境要求

| 依赖 | 版本 | 说明 |
|---|---|---|
| Python | 3.11+ | 后端 |
| Node.js | 18+ | 前端 |
| [uv](https://docs.astral.sh/uv/) | 最新 | Python 包/环境管理 |
| LLM 端点 | OpenAI 兼容 | 默认用腾讯混元 Hy3 |
| 操作系统 | macOS（推荐 Apple Silicon） | 扫描件 OCR 用 MinerU + MPS；其他平台可用 CPU |

> 首次运行会自动下载 sentence-transformers 向量模型（约 120MB）；首次处理扫描件时会下载 MinerU 模型（数 GB），请预留磁盘与网络。

---

## 快速开始

### 1. 后端

```bash
cd server
cp .env.example .env
# 编辑 .env，至少填入 HY3_API_KEY 与 HY3_BASE_URL
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

验证：

```bash
curl http://localhost:8000/health   # {"status":"ok"}
```

### 2. 前端

```bash
cd web
npm install
npm run dev
# 打开 http://localhost:5173
```

### 3. MinerU（扫描件 OCR）

无需手动启动，`uv sync` 已安装，后端遇到扫描页时自动调用。首次处理扫描件会下载模型，国内网络可将模型源切到 ModelScope：

```bash
# 写入 server/.env
MINERU_MODEL_SOURCE=modelscope
```

内存紧张时调小 `HYGRAPH_MINERU_VRAM`（默认 8GB）。

---

## 环境变量

在 `server/.env` 中配置（`.env` 不进版本控制，`.env.example` 为占位模板）。

| 变量 | 必需 | 默认 | 说明 |
|---|---|---|---|
| `LLM_PROVIDER` | | `hy3` | LLM provider：`hy3` / `openrouter` / `ollama` |
| `HY3_API_KEY` | ✅ | — | Hy3 API 密钥（`hy3` 时必需） |
| `HY3_BASE_URL` | ✅ | — | Hy3 端点，如 `https://<host>/v1` |
| `HY3_MODEL` | | `hy3` | 模型名 |
| `OPENROUTER_API_KEY` | | — | OpenRouter 密钥（`openrouter` 时必需） |
| `OPENROUTER_BASE_URL` | | `https://openrouter.ai/api/v1` | OpenRouter 端点 |
| `OPENROUTER_MODEL` | | `tencent/hy3` | OpenRouter 模型标识 |
| `OLLAMA_BASE_URL` | | — | Ollama 服务地址（`ollama` 时必需） |
| `OLLAMA_MODEL` | | — | Ollama 模型名（`ollama` 时必需） |
| `DB_PATH` | | `data/hygraph.db` | SQLite 路径 |
| `HOST` | | `0.0.0.0` | 服务监听地址 |
| `PORT` | | `8000` | 服务端口 |
| `BACKGROUND_COMPILE_CONCURRENCY` | | `2` | 后台预编译并发度 |
| `HYGRAPH_MINERU_VRAM` | | `8` | MinerU 虚拟显存预算（GB） |
| `MINERU_MODEL_SOURCE` | | `huggingface` | MinerU 模型源，国内可设 `modelscope` |
| `MINERU_CMD` | | `mineru` | 自定义 mineru 可执行文件路径 |

---

## 使用流程

1. 进入「文档中心」上传文档。
2. 等待状态变为「就绪」（扫描件走 OCR 会较慢）。
3. 在问答视图选择 0~n 个文档作为问答范围（不选则检索全部）。
4. 提问，获得带页码溯源的回答；展开「来源引用」查看命中原文。
5. 切到「思维导图 / 知识图谱」浏览文档结构。

---

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | React 19 + TypeScript + Vite 8 + Zustand 5 + @antv/g6 v5 + Tailwind CSS + KaTeX |
| 后端 | Python 3.11+ + FastAPI + SQLite + uv |
| PDF 解析 | PyMuPDF4LLM（文本层）+ MinerU（扫描件 OCR） |
| 向量化 | sentence-transformers（768 维本地模型） |

---

## Demo

端到端演示流程:[点击查看](https://www.bilibili.com/video/BV1uLKb67EbG/)


---

## 常见问题

- **启动报「缺少必需配置」**：`server/.env` 未填 `HY3_API_KEY` / `HY3_BASE_URL`。
- **扫描件处理慢**：OCR 本身较慢，进度条平滑推进即为正常；内存紧张可调小 `HYGRAPH_MINERU_VRAM`。

## 许可证

Apache-2.0
