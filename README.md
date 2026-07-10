# Hy3 知识库问答 MCP Server

一个基于 **MCP（Model Context Protocol）** 协议、内部调用 **Hy3（腾讯 TokenHub）后端大模型 API** 的「知识库问答」MCP Server。它把 Hy3 的能力封装为若干开箱即用的 MCP tool，可被任意支持 MCP 的客户端（CodeBuddy / Cursor / Cline / Open WebUI 等）即插即用。

- 兼容 OpenAI Chat Completions 协议接入 Hy3（`hy3` 模型，端点 `https://tokenhub.tencentmaas.com/v1`）
- 本地 **stdio** 模式运行，无需公网部署
- **零额外依赖**的轻量 BM25 检索（无向量库、无 embedding 服务）
- 默认支持纯文本格式：`.txt` / `.md` / `.csv`
- **绝不在代码中硬编码 API Key**，密钥仅通过环境变量传入

> **⚠️ 重要概念区分（避免混淆）**
> 本项目里的「Hy3 / 腾讯」指的是 **MCP server 内部调用的后端大模型 API**，由 `HY3_API_KEY` + `HY3_BASE_URL` 配置，**只用于** `ask_knowledge` / `summarize_document` / `chat_hy3` 三个真正调模型的 tool。
> 它与**你所用 MCP 客户端（CodeBuddy / Cline 等）自己的推理模型完全无关**——例如 Cline 里的 `tencent/hy3:free` 是 OpenRouter 上的腾讯混元免费档，由 Cline 自己的账号 / token 控制。
> 两者仅名字里都带 "hy3"，但**是两套独立认证、独立端点、互不影响**：server 的 key 失效不会让客户端 retry，客户端的模型限流也不会让 server 报错。详见文末「常见问题」。

---

## 1. 功能（MCP Tool 一览）

| Tool | 参数 | 功能 | 数据源 / 核心 |
|---|---|---|---|
| `load_knowledge` | `paths: list[str]` | 解析并切片入库，返回入库块数 | 本地文件读取 |
| `search_knowledge` | `query: str, top_k: int = 5` | 基于 BM25 召回相关片段（**不调用任何模型**） | 本地索引 |
| `ask_knowledge` | `question: str, top_k: int = 5, include_sources: bool = True` | 召回上下文 → 调 Hy3 后端生成**带引用**的答案 | **Hy3 API（`HY3_API_KEY`）** |
| `summarize_document` | `path: str` | 调 Hy3 后端对单个文档做摘要 | **Hy3 API（`HY3_API_KEY`）** |
| `chat_hy3` | `message: str, system_prompt: str = "", temperature: float = 0.7` | 直连 Hy3 后端通用推理 | **Hy3 API（`HY3_API_KEY`）** |

> 注意：只有后三个 tool 会用到 `HY3_API_KEY`；`load_knowledge` / `search_knowledge` 完全本地运行，即使没有 key 也能正常工作。

每个 tool 都包含清晰的名称、参数描述与功能说明（由 docstring 自动生成 MCP schema）。

---

## 2. 安装

### 方式一：本地源码安装（推荐，无需发版）

```bash
# 1) 克隆 / 解压本项目后进入目录
cd hy3-kb-mcp

# 2) （可选）创建虚拟环境
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3) 安装
pip install .
```

安装后会在环境中生成控制台命令 **`hy3-kb-mcp`**（Windows 下位于 `PythonXX\Scripts\hy3-kb-mcp.exe`）：

```bash
hy3-kb-mcp --help   # 验证安装成功
```

### 方式二：从源码直接运行（不安装控制台命令）

```bash
pip install -e .        # 可编辑安装，等价于方式一
# 或
python -m hy3_mcp       # 直接用解释器跑模块（无需 console script）
```

> 依赖：`mcp`（官方 SDK，FastMCP）、`openai`（接入 Hy3）。Python ≥ 3.10。

---

## 3. 配置（环境变量）

所有密钥与端点均通过环境变量设置，**代码中无硬编码**。

| 变量 | 必填 | 默认值 | 说明 |
|---|---|---|---|
| `HY3_API_KEY` | ✅（仅调模型类 tool 需要） | — | Hy3 / 腾讯 TokenHub API Key |
| `HY3_BASE_URL` | ❌ | `https://tokenhub.tencentmaas.com/v1` | Hy3 后端 API 端点 |
| `HY3_MODEL` | ❌ | `hy3` | 模型名 |
| `HY3_KB_STORE` | ❌ | `./.hy3_kb_store.json` | 知识库索引持久化路径 |
| `HY3_MAX_CONTEXT_CHARS` | ❌ | `12000` | 喂给模型的最大上下文字符数 |

获取 Hy3 API Key 后，在启动 MCP 客户端前导出：

```bash
export HY3_API_KEY="你的Key"
```

Windows（PowerShell）：

```powershell
$env:HY3_API_KEY="你的Key"
```

---

## 4. 客户端接入

### 4.1 CodeBuddy / WorkBuddy（项目级）

在项目根目录**新建** `.codebuddy/mcp.json`（如不存在）：

```json
{
  "mcpServers": {
    "hy3-knowledge-base": {
      "command": "hy3-kb-mcp",
      "env": {
        "HY3_API_KEY": "你的Key"
      }
    }
  }
}
```

或使用 CLI 添加：

```bash
codebuddy mcp add -s project hy3-knowledge-base -- hy3-kb-mcp
```

> 提示：若 `hy3-kb-mcp` 不在 PATH，可改用**绝对路径**，见文末「常见问题 · Windows 路径」。

### 4.2 Cline（VS Code 插件）

1. 打开 Cline 插件的 **MCP Servers → Configure**（或编辑其全局配置文件 `cline_mcp_settings.json`）。
2. 加入如下配置（本仓库未内置该文件，请直接照抄；将它放在 Cline 的 MCP 配置文件里即可）：

```json
{
  "mcpServers": {
    "hy3-knowledge-base": {
      "command": "hy3-kb-mcp",
      "env": {
        "HY3_API_KEY": "你的Key"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

3. 重启 / 刷新 Cline，确认 `hy3-knowledge-base` 状态为已连接。

---

## 5. 可运行使用示例（Demo）

在两个客户端中均可执行以下两步：

**第 1 步：载入知识库**

调用 `load_knowledge`，参数 `paths` 传入示例文档目录。
**建议用绝对路径**（server 的工作目录不一定等于项目根目录，相对路径可能找不到文件）：

```text
paths = ["examples/sample_docs"]
# 更稳妥（尤其 Cline / 远程场景），用绝对路径：
paths = ["C:/abs/path/to/your/project/examples/sample_docs"]
```

返回示例：

```
Loaded 3 file(s), added 5 chunk(s). Total chunks in KB: 5.
```

**第 2 步：基于知识库提问**

调用 `ask_knowledge`：

```text
question = "这个知识库支持哪些文件格式？"
```

返回示例（含引用）：

```
默认安装下，知识库支持纯文本类文件：.txt、.md/.markdown 以及 .csv。
如需 PDF / Word，可通过可选 extras 安装 pypdf / python-docx。

---
Sources:
[1] examples/sample_docs/overview.md
    本仓库是一个基于 MCP（Model Context Protocol）协议...
```

**其他 tool 试一下：**

- `search_knowledge(query="BM25", top_k=3)` —— 仅检索，不调模型（**无需 `HY3_API_KEY`**）。
- `summarize_document(path="examples/sample_docs/faq.md")` —— 文档摘要。
- `chat_hy3(message="用一句话解释什么是 MCP")` —— 直连 Hy3 后端通用推理。

---

## 6. 本地验证（无需 GUI 客户端）

### 6.1 单元测试（离线，不调用 Hy3）

```bash
pip install -e ".[dev]"
pytest -q
```

测试覆盖：BM25 排序、文件解析、知识库入库/持久化、各 tool 逻辑（Hy3 已 mock）。

### 6.2 MCP 协议层自检（MCP Inspector）

```bash
npx @modelcontextprotocol/inspector hy3-kb-mcp
```

在浏览器中可看到 5 个 tool 及其 schema，并直接调用验证。

### 6.3 真实调用（需要 Key）

```bash
export HY3_API_KEY="你的Key"
hy3-kb-mcp
```

然后用任意支持 stdio MCP 的客户端接入即可。

---

## 7. 项目结构

```
hy3-kb-mcp/
├── pyproject.toml            # 打包 + 控制台入口 hy3-kb-mcp
├── README.md
├── LICENSE
├── .gitignore
├── src/hy3_mcp/              # ← MCP server 包（核心代码，见文末说明）
│   ├── __init__.py
│   ├── __main__.py           # python -m hy3_mcp
│   ├── server.py             # FastMCP + 5 个 tool
│   ├── hy3_client.py         # Hy3 OpenAI 兼容客户端（读环境变量）
│   ├── knowledge_base.py     # 分块 + 索引（持久化到本地 JSON）
│   ├── retrievers.py         # 轻量 BM25 检索（无外部依赖）
│   ├── parsers.py            # txt/md/csv 解析
│   └── config.py             # 环境变量加载
├── examples/
│   └── sample_docs/          # 演示用文档
└── tests/test_server.py      # 离线自测
```

---

## 8. 常见问题

**Q：知识库会持久化吗？**
会。默认持久化到 `./.hy3_kb_store.json`，可用 `HY3_KB_STORE` 修改路径；重启 server 后自动加载。

**Q：支持 PDF / Word 吗？**
默认仅 `.txt/.md/.csv`（零额外依赖）。如需 PDF/Word，安装可选 extras：`pip install ".[pdf,docx]"`，并在 `parsers.py` 中启用对应分支（已预留 `UnsupportedFileType` 提示）。

**Q：检索不准怎么办？**
默认是词法 BM25，适合关键词重合度高的场景。如需语义检索，可后续接入 embedding 服务替换 `retrievers.py`。

**Q：Windows 下 `hy3-kb-mcp` 命令找不到 / 启动报错？**
确保安装在当前 Python 环境且已激活；或在客户端配置里用**绝对路径**。
注意：JSON 配置里**务必用正斜杠 `/`**——不要用单反斜杠 `\`（它会被 JSON 转义吃掉，导致命令解析失败、server 启动不了）。例如：

```json
"command": "C:/Users/you/AppData/Local/Programs/Python/Python310/Scripts/hy3-kb-mcp.exe"
```

若 console script 未生成，也可改用模块形式：`"command": "C:/.../Python310/python.exe", "args": ["-m", "hy3_mcp"]`。

**Q：MCP server 显示已连接，但客户端调用时一直 retry / 报错？**
先分清"谁在报错"：`hy3-knowledge-base` 在客户端里显示**已连接**，说明 server 进程正常、5 个 tool 已注册成功。
若调用时客户端（如 Cline）反复 retry，而 server 自身没有报错日志，通常是**客户端自身**的问题：

- 客户端自己的模型（如 Cline 的 `tencent/hy3:free` 免费档）被限流；或
- 客户端向自身后端刷新登录 token 失败（如 Cline 的 `api.cline.bot`）。

这与本 server 的 `HY3_API_KEY` **无关**——`HY3_API_KEY` 只影响 `ask_knowledge` 等三个调模型的 tool，且失效时会在 tool 返回里明确提示 `Hy3 API call failed`，**不会**让客户端整体 retry。
排查：先用**不调模型**的 `search_knowledge` 测试；若它能返回结果，则 server 与 key 均正常，问题在客户端侧（换模型 / 重登客户端账号）。

---

## License

MIT © Rhino Bird MCP Contest
