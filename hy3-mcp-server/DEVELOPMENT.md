# Hy3 MCP Server 技术说明文档

## 一句话总结


---

## 用到了哪些技术？

| 技术 | 是什么 | 在项目中干什么 |
|------|--------|----------------|
| **MCP 协议** | Model Context Protocol，一种让 AI 客户端和工具服务器通信的标准协议 | 定义了客户端怎么"发现"和"调用"我们写的工具 |
| **FastMCP** | Anthropic 官方出的 Python 框架，用来快速搭建 MCP Server | 我们用它来注册工具、处理客户端请求，不用手写底层通信代码 |
| **OpenAI Python SDK** | OpenAI 官方的 Python 库，用来调用大模型 API | Hy3 的 API 和 OpenAI 格式兼容，所以直接用这个库调 Hy3 |
| **pypdf** | Python 的 PDF 解析库 | 读取 PDF 文件内容 |
| **python-docx** | Python 的 Word 文档解析库 | 读取 .docx 文件内容 |
| **python-dotenv** | 从 .env 文件读取环境变量的库 | 避免把 API Key 写死在代码里 |

---

## 整体架构图（简化版）

```
你在 Cursor 里打字提问
        │
        ▼
┌──────────────┐    MCP 协议（stdio）    ┌──────────────────┐
│   Cursor     │ ◄──────────────────────► │  我们的 Server   │
│  (AI客户端)  │    标准化的通信方式       │                  │
└──────────────┘                         │  ① 接收请求      │
                                         │  ② 读文件/调API  │
                                         │  ③ 返回结果      │
                                         └──────────────────┘
                                                  │
                                    ┌─────────────┼─────────────┐
                                    ▼             ▼             ▼
                              读本地文件     调用Hy3 API    解析PDF/DOCX
```

---

## 核心概念解释

### 1. MCP（Model Context Protocol）是什么？

你可以把它理解为 **AI 世界的 USB 接口**：

- 没有 MCP 之前：每个 AI 客户端想用外部工具，都得单独写对接代码，就像每个设备用自己的充电线
- 有了 MCP 之后：只要工具实现了 MCP 协议，任何 AI 客户端都能即插即用，就像 USB 设备插上就能用

**MCP 的两种通信方式：**
- `stdio`（本项目用的）：Server 作为子进程运行，通过标准输入/输出通信，适合本地使用
- `SSE/HTTP`：通过网络通信，适合远程部署

### 2. FastMCP 是什么？

它是 MCP 协议的 Python 快速开发框架，**你只需要写工具函数，框架帮你搞定通信**。

没有 FastMCP，你需要手写：
```python
# 大约需要 200+ 行底层代码
async def handle_request(request):
    if request.method == "tools/list":
        # 手动序列化工具列表
    elif request.method == "tools/call":
        # 手动解析参数、调用函数、序列化结果
    # ... 还要处理 JSON-RPC 协议细节
```

有了 FastMCP，只需要：
```python
from fastmcp import FastMCP

mcp = FastMCP("my-server")

@mcp.tool()                    # 这个装饰器就搞定了注册+通信
def read_file(file_path: str):  # 函数签名自动变成参数描述
    """读取文件内容"""           # docstring 自动变成工具说明
    return open(file_path).read()

mcp.run(transport="stdio")     # 一行启动
```

### 3. 为什么用 OpenAI SDK 调 Hy3？

因为 Hy3 的 API 是 **OpenAI 兼容格式**：

```python
# 调 Hy3 和调 OpenAI 的代码几乎一样，只改 base_url
from openai import OpenAI

client = OpenAI(
    api_key="你的Key",
    base_url="https://tokenhub.tencentmaas.com/v1",  # 换成 Hy3 的地址
)

response = client.chat.completions.create(
    model="hy3",    # 换成 Hy3 的模型名
    messages=[{"role": "user", "content": "你好"}],
)
```

这意味着你不需要学新的 SDK，用熟悉的 OpenAI 写法就能调 Hy3。

---

## 项目文件说明

```
hy3-mcp-server/
├── src/hy3_mcp_server/
│   ├── __init__.py        # 空文件，标记这是一个 Python 包
│   ├── server.py          # 核心！定义了 4 个工具和 MCP Server
│   └── hy3_client.py      # 封装了 Hy3 API 的调用逻辑
│
├── pyproject.toml         # Python 项目配置（依赖、入口点等）
├── requirements.txt       # 依赖列表（pip install -r 这个文件装依赖）
├── .env.example           # 环境变量模板（告诉你需要配哪些变量）
├── .gitignore             # Git 忽略规则
└── README.md              # 使用说明
```

### server.py 核心代码流程

```python
# 1. 创建 MCP Server 实例
mcp = FastMCP("hy3-knowledge-base")

# 2. 注册工具（@mcp.tool() 装饰器）
@mcp.tool()
def read_file(file_path: str, max_chars: int = 50000) -> str:
    """读取本地文件内容"""           # ← 这个 docstring 会变成工具描述
    content = _read_file_content(file_path)
    return _truncate(content, max_chars)
    # ↑ 函数的参数和类型注解会自动生成 MCP 的参数 schema

# 3. 启动 Server
def main():
    mcp.run(transport="stdio")     # 以 stdio 模式启动，等待客户端连接
```

### hy3_client.py 核心逻辑

```python
def chat(messages, temperature=0.7, reasoning_effort="no_think"):
    """向 Hy3 发送对话请求并返回回复"""
    client = OpenAI(
        api_key=os.environ["HY3_API_KEY"],    # 从环境变量读取，不硬编码
        base_url=os.environ.get("HY3_BASE_URL", "https://tokenhub.tencentmaas.com/v1"),
    )
    response = client.chat.completions.create(
        model=os.environ.get("HY3_MODEL", "hy3"),
        messages=messages,
        extra_body={"chat_template_kwargs": {"reasoning_effort": reasoning_effort}},
    )
    return response.choices[0].message.content
```

---

## 4 个工具是怎么工作的？

### 工具 1：`read_file` — 读取文件

```
用户说："帮我读一下 report.pdf"
    → Cursor 调用 read_file(file_path="report.pdf")
    → Server 读取 PDF 内容
    → 返回文本给 Cursor
```

这个工具不调 Hy3，只做文件读取，让 AI 客户端先拿到文件内容。

### 工具 2：`ask_about_documents` — 基于文档问答

```
用户说："根据 README.md，这个项目怎么安装？"
    → Cursor 调用 ask_about_documents(file_paths=["README.md"], question="怎么安装？")
    → Server 读取 README.md 内容
    → 把文件内容 + 问题一起发给 Hy3
    → Hy3 基于文档内容回答
    → 返回回答给 Cursor
```

这是核心工具，实现了"先读文档，再让 Hy3 基于文档回答"。

### 工具 3：`summarize_document` — 文档摘要

```
用户说："帮我总结一下这篇论文"
    → Cursor 调用 summarize_document(file_path="paper.pdf", summary_type="bullet")
    → Server 读取论文内容
    → 把内容 + 摘要指令发给 Hy3
    → 返回摘要结果
```

### 工具 4：`search_files_and_answer` — 搜索文件并回答

```
用户说："src 目录下代码是怎么处理错误的？"
    → Cursor 调用 search_files_and_answer(directory="src", query="错误处理")
    → Server 扫描 src 目录，找到匹配文件
    → 读取文件内容
    → 把内容 + 问题发给 Hy3
    → 返回回答
```

这个工具额外接入了"本地文件系统搜索"作为外部数据源。

---

## 为什么 API Key 要用环境变量？

```python
# ❌ 错误：硬编码 Key
api_key = "sk-abc123..."

# ✅ 正确：从环境变量读取
api_key = os.environ["HY3_API_KEY"]
```

原因：
1. **安全**：代码上传到 GitHub 后，硬编码的 Key 会泄露，别人能用你的额度
2. **灵活**：不同环境（开发/生产）可以用不同的 Key，改环境变量就行，不用改代码
3. **规范**：这是行业通行做法，几乎所有云服务都要求这样做

---

## 常见问题

**Q：为什么选 stdio 模式而不是网络模式？**
A：stdio 模式最简单，MCP 客户端直接启动 Server 子进程，不需要配置端口和网络，适合本地开发使用。

**Q：Hy3 的 reasoning_effort 参数是什么？**
A：控制 Hy3 的"思考深度"：`no_think` 直接回答（快），`low` 浅度思考，`high` 深度推理（慢但更准，适合复杂问题）。

**Q：fastmcp 和 mcp（官方 SDK）有什么区别？**
A：`mcp` 是底层 SDK，需要手写很多协议处理代码；`fastmcp` 是上层框架，用装饰器就能注册工具，开发效率高很多。类比：`mcp` 像 Flask，`fastmcp` 像 FastAPI。

**Q：为什么不自己训练模型，而是调 API？**
A：Hy3 有 295B 参数，需要 8 张 H20 GPU 才能跑起来，对大多数人来说直接调 API 是最经济的方案。
