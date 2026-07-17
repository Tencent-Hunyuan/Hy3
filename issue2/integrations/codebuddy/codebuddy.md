# 在 CodeBuddy / WorkBuddy 中使用 Hy3

> 🌐 English version: [codebuddy.en.md](codebuddy.en.md)

## 工具简介

[CodeBuddy](https://www.codebuddy.ai) 是一款 AI 驱动的全栈开发助手，WorkBuddy 是其工作流自动化版本。它们支持**自定义模型接入**，可以将 Hy3 配置为后端推理引擎，用于代码生成、项目搭建、自动化工作流编排。

## 适用场景

- 全栈项目从零生成（前端 + 后端 + 数据库）
- AI 驱动的 PR Review、代码审查
- 自动化工作流：文档生成、测试用例生成、CI/CD 脚本

## 版本要求

| 项 | 要求 |
|:---|:---|
| CodeBuddy 版本 | ≥ 1.0（推荐最新版） |
| Hy3 服务 | 自建 OpenAI 兼容 API 端点 |

## 配置项

### CodeBuddy Provider 配置

在 CodeBuddy 的 **Provider 设置** 中添加自定义 Provider：

```yaml
# 或通过 UI 配置面板填写
provider:
  name: "Hy3"
  type: "openai-compatible"
  base_url: "https://tokenhub.tencentmaas.com/v1"
  api_key: "your-api-key"
  default_model: "hy3"

  # 可选：模型参数默认值
  default_params:
    temperature: 0.9
    top_p: 1.0
    max_tokens: 8192
    reasoning_effort: "high"  # Agent 模式下推荐
```

### 不同工作模式的推荐参数

| 工作模式 | `reasoning_effort` | `temperature` | `max_tokens` |
|:---|:---|:---|:---|
| 代码生成 (Chat) | `high` | 0.9 | 4096 |
| 代码补全 (Complete) | `low` | 0.6 | 1024 |
| PR Review (Agent) | `high` | 0.3 | 8192 |
| 文档生成 (Agent) | `low` | 0.9 | 16384 |
| 工作流编排 (WorkBuddy) | `high` | 0.9 | 8192 |

## 端到端 Demo：用 CodeBuddy + Hy3 构建一个 REST API 项目

### Prompt（在 CodeBuddy Chat 中输入）

```
用 Python FastAPI 创建一个图书管理 REST API：
1. 包含 Book 的 CRUD 操作（创建/读取/更新/删除）
2. 使用 SQLite（aiosqlite）异步数据库
3. 完整的 Pydantic 模型定义和请求验证
4. Swagger 文档自动生成
5. 包含错误处理和日志记录
6. 写 docker-compose.yml 用于部署
```

### Hy3 生成的典型项目结构

```
book-api/
├── main.py              # FastAPI 入口
├── models.py            # Pydantic 模型
├── database.py          # SQLite 异步操作
├── routes.py            # 路由定义
├── requirements.txt     # 依赖
├── Dockerfile           # 容器化
└── docker-compose.yml   # 部署编排
```

### 核心代码预览（Hy3 生成）

```python
# main.py
from fastapi import FastAPI
from routes import router

app = FastAPI(
    title="图书管理 API",
    description="使用 FastAPI + SQLite 的图书管理系统",
    version="1.0.0"
)
app.include_router(router, prefix="/api/v1")

# models.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class BookCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    author: str = Field(..., min_length=1, max_length=100)
    isbn: str = Field(..., pattern=r"^\d{10}|\d{13}$")
    published_year: Optional[int] = Field(None, ge=1900, le=2026)

class BookResponse(BookCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# routes.py
from fastapi import APIRouter, HTTPException, Query
from models import BookCreate, BookResponse
from database import BookDB

router = APIRouter()
db = BookDB("books.db")

@router.get("/books", response_model=list[BookResponse])
async def list_books(page: int = Query(1, ge=1), size: int = Query(20, le=100)):
    """获取图书列表，支持分页"""
    return await db.list(page, size)

@router.post("/books", response_model=BookResponse, status_code=201)
async def create_book(book: BookCreate):
    """创建新图书"""
    return await db.create(book)

@router.get("/books/{book_id}", response_model=BookResponse)
async def get_book(book_id: int):
    """获取单本图书详情"""
    result = await db.get(book_id)
    if not result:
        raise HTTPException(status_code=404, detail="Book not found")
    return result

@router.put("/books/{book_id}", response_model=BookResponse)
async def update_book(book_id: int, book: BookCreate):
    """更新图书信息"""
    result = await db.update(book_id, book)
    if not result:
        raise HTTPException(status_code=404, detail="Book not found")
    return result

@router.delete("/books/{book_id}", status_code=204)
async def delete_book(book_id: int):
    """删除图书"""
    deleted = await db.delete(book_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Book not found")
```

### WorkBuddy 自动化工作流示例

```yaml
# workbuddy-hy3.yaml
name: "PR Review Pipeline"
trigger:
  on: "pull_request"
  branches: ["main", "develop"]

jobs:
  code-review:
    runs-on: "hy3-agent"
    steps:
      - name: "Review code changes"
        provider: "hy3"
        prompt: |
          请审查本次 PR 的代码变更：
          1. 检查代码风格和最佳实践
          2. 识别潜在的安全漏洞
          3. 评估性能影响
          4. 提供改进建议（以 markdown 格式输出）

      - name: "Generate CHANGELOG"
        provider: "hy3"
        prompt: |
          根据本次 PR 的变更，生成 CHANGELOG 条目（中文）。
```

## 常见注意事项

| 问题 | 原因 | 解决方案 |
|:---|:---|:---|
| Provider 连接失败 | `base_url` 或端口错误 | 在终端 `curl` 测试服务可用性 |
| 生成代码质量不稳定 | `temperature` 过高 | Agent 模式下降到 `0.3-0.6` |
| WorkBuddy 流程中断 | 单步超时 | 增大超时时间或拆分为更小的步骤 |
| 文件结构不完整 | 单次生成 token 不足 | 增大 `max_tokens` 到 8192+ |
| 长任务上下文丢失 | 超长项目描述超出上下文 | 分段描述，先搭建骨架再细化 |


[← 返回索引](../README.md)
