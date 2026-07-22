# HyGraph · 通用文档知识问答系统

上传任意文档（扫描件 / 文本 PDF、Word、PPT、Excel、EPUB、Markdown、TXT），系统在本地转写并**轻结构化为「知识页」**；提问时按导航优先召回命中整页原文，喂给大模型**只读作答**并标注文件名 + 页码 + 原文片段。

- **文档全局化**：文档是全局资源，与会话解耦，可跨会话复用（详见 `docs/016`）。
- **章节级粒度**：PDF 优先用内嵌书签（大纲）划分章节，无书签则按标题识别；超大节点再按页强制切分，保证知识页粒度可控、召回精准（`docs/018` / `docs/019`）。
- **扫描件 OCR**：扫描页走本地 MinerU（Apple Silicon 自动用 MPS 加速），文本层页走 PyMuPDF4LLM 快路径，二者可在同一 PDF 内混合处理（`docs/017` / `docs/020`）。

---
# Hy3 在系统中承担的角色
 

1. **结构化抽取**：接收原始文本 / 主题，输出规范的图谱 JSON（nodes + edges）
2. **两种模式**：思维导图（层级主题树）/ 知识图谱（实体 + 语义关系）
3. **问答**：Hy3 流式回答

Hy3 通过 OpenAI 兼容 `chat.completions` 协议接入，`reasoning_effort` 设 `low`（结构化抽取）/ `no_think`（流式问答）。

---

## 一、环境要求

| 依赖 | 版本 | 说明 |
|---|---|---|
| Python | 3.11+ | 后端 |
| Node.js | 18+ | 前端 |
| [uv](https://docs.astral.sh/uv/) | 最新 | Python 包/环境管理 |
| LLM 端点 | OpenAI 兼容 | 提供 `chat.completions`，用于问答作答 |
| 操作系统 | macOS（推荐 Apple Silicon） | 扫描件 OCR 用 MinerU + MPS；其他平台可用 CPU |

> 首次运行会自动下载两类模型：sentence-transformers 向量模型（约 120MB）、以及**首次处理扫描件时**下载的 MinerU 模型（数 GB）。请预留磁盘与网络。

---

## 二、启动步骤

三部分：**后端**、**前端**、**MinerU**。MinerU 无需单独启动——它作为后端的 Python 依赖安装，处理扫描件时由后端自动以子进程调用。

### 1. 后端

```bash
cd server

# 配置 LLM（OpenAI 兼容）等环境变量
cp .env.example .env
# 编辑 .env，至少填入 HY3_API_KEY 与 HY3_BASE_URL（见下方环境变量表）

# 安装依赖（含 mineru[core]，首次较慢）
uv sync

# 启动（开发模式，热重载）
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动时会做：配置校验（缺 `HY3_API_KEY` / `HY3_BASE_URL` 直接报错，Fail Fast）→ 初始化 SQLite 表 → 自动迁移。验证：

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

前端 dev server 默认 `5173`，已在后端 CORS 白名单内。生产构建：`npm run build`（产物在 `web/dist`），预览：`npm run preview`。

### 3. MinerU（扫描件 OCR）

- **无需手动启动**：`uv sync` 已装好 `mineru[core]`，后端在遇到扫描页时自动调用本地 `mineru` CLI（pipeline 后端）。
- **模型下载**：首次处理扫描件会自动下载 MinerU 模型（数 GB）。国内网络可将模型源切到 ModelScope：

```bash
# 写入 server/.env
MINERU_MODEL_SOURCE=modelscope
```

- **设备与内存**：Apple Silicon 上 MinerU 自动使用 MPS。通过 `HYGRAPH_MINERU_VRAM`（GB）调节批推理大小——**同时是速度与峰值内存的旋钮**：内存吃紧（如同时开 IDE）调小（如 `4`），追求速度调大（如 `16`），默认 `8`。
- **自检**：确认可执行文件存在：

```bash
cd server && uv run mineru --help
```

---

## 三、环境变量

在 `server/.env` 中配置（`.env` 不进版本控制，`.env.example` 为占位模板）。

| 变量 | 必需 | 默认 | 说明 |
|---|---|---|---|
| `HY3_API_KEY` | ✅ | — | LLM API 密钥（OpenAI 兼容） |
| `HY3_BASE_URL` | ✅ | — | LLM 端点，如 `https://<host>/v1` |
| `HY3_MODEL` | | `hy3` | 模型名 |
| `DB_PATH` | | `data/hygraph.db` | SQLite 路径 |
| `HOST` | | `0.0.0.0` | 服务监听地址 |
| `PORT` | | `8000` | 服务端口 |
| `BACKGROUND_COMPILE_CONCURRENCY` | | `2` | 后台预编译并发度 |
| `HYGRAPH_MINERU_VRAM` | | `8` | MinerU 虚拟显存预算（GB），控速度/内存 |
| `MINERU_MODEL_SOURCE` | | `huggingface` | MinerU 模型源，国内可设 `modelscope` |
| `MINERU_DEVICE_MODE` | | 自动 | 强制设备 `mps`/`cuda`/`cpu`，一般无需设置 |
| `MINERU_CMD` | | `mineru` | 自定义 mineru 可执行文件路径 |

> 环境变量名沿用 `HY3_*` 是历史命名，实为任意 OpenAI 兼容端点，与具体厂商无关。

---

## 四、使用流程

1. 进入「文档中心」上传文档（PDF / Word / PPT / Excel / EPUB / Markdown / TXT）。
2. 状态流转：待处理 → 处理中 → 就绪。扫描件走 OCR 会较慢，进度条会平滑推进（非卡死）。
3. 回到问答视图，在输入区选择 0~n 个文档作为本次问答范围（不选则默认检索全部就绪文档）。
4. 提问，获得带段末页码溯源的回答；展开「来源引用」查看命中原文片段（刷新会话后仍保留）。
5. 切到「思维导图 / 知识图谱」浏览由知识页派生的结构与双链关系。

---

## 五、架构概览

「最难的理解与合成放到入库期一次做好，查询期退化为读整页 + 照抄 + 标页码」。

| 阶段 | 承担方 | 说明 |
|---|---|---|
| 文档转写 | PyMuPDF4LLM / MinerU / python-docx 等（本地） | 多模态 → 带页码的规范 markdown 结构树，零 token |
| 章节结构 | `transcribe/loader.py`（本地） | 书签优先 → 标题识别 → 超大节点按页切分 |
| 知识页编译 | `agents/wiki_compiler.py`（本地） | M1-M4 机械提取：保真正文 + 索引 + 双链 + 来源锚点，默认不调 LLM |
| 向量化 | sentence-transformers（本地） | 768 维本地模型，零 token |
| 召回 | `agents/recall.py` | 精确命中 → 术语映射 → embedding 兜底 → 原文兜底，整页注入 1~3 页 |
| 问答作答 | LLM（OpenAI 兼容，SSE 流式） | 只读命中知识页原文，段末标注文件名 + 页码 |
| 可视化 | @antv/g6 v5（前端） | 由知识页双链派生，仅用于浏览 |

---

## 六、技术栈

| 层 | 技术 |
|---|---|
| 前端 | React 19 + TypeScript + Vite 8 + Zustand 5 + @antv/g6 v5 + Tailwind CSS + react-markdown + KaTeX |
| 后端 | Python 3.11+ + FastAPI + langchain-openai + SQLite + uv |
| PDF 解析 | PyMuPDF4LLM（文本层）+ MinerU（扫描件 OCR，含公式/表格） |
| Office / 电子书 | python-docx / python-pptx / openpyxl / ebooklib |
| 向量化 | sentence-transformers（768 维本地模型） |
| 公式渲染 | KaTeX（前端） |

---
 
  
