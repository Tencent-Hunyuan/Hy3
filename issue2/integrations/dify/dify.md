# 在 Dify 中使用 Hy3

> 🌐 English version: [dify.en.md](dify.en.md)

## 工具简介

[Dify](https://dify.ai) 是一个开源的 LLM 应用开发平台，支持可视化编排 AI 工作流、RAG 知识库、Agent 工具调用。作为低代码平台，Dify 内置了对 **OpenAI 兼容 API** 的支持，可以无缝接入 Hy3。

## 适用场景

- 低代码搭建 Hy3 驱动的 ChatBot / 客服系统
- 基于 Hy3 的内容生成流水线（批量写作、翻译、摘要）
- RAG 知识库问答（Hy3 长上下文 + 知识库检索增强）
- 多步骤 Agent 工作流（Hy3 推理 + 工具调用 + 条件分支）

## 版本要求

| 项 | 要求 |
|:---|:---|
| Dify 版本 | ≥ 0.6.0（社区版 / 云版均可） |
| 部署方式 | Docker Compose（推荐）或 Dify Cloud |
| Hy3 服务 | 自建 OpenAI 兼容 API 端点 |

## 配置项

### 步骤 1：添加 Hy3 模型供应商

1. 登录 Dify → 右上角头像 → **设置** → **模型供应商**
2. 找到 **OpenAI-API-compatible** → 点击 **添加模型**
3. 填写配置：

```
模型名称：          hy3
模型类型：          LLM
API 端点 URL：     https://tokenhub.tencentmaas.com/v1
API Key：          your-api-key
模型名称（API 参数）： hy3
```

4. 点击 **保存**，Dify 会自动测试连接。

### 步骤 2：在应用中选择 Hy3

创建或编辑应用 → **模型设置** → 选择 `OpenAI-API-compatible` → `hy3`

### 关键参数映射

| Hy3 参数 | Dify 配置 |
|:---|:---|
| `temperature=0.9` | 应用 → 模型参数 → Temperature 设为 `0.9` |
| `top_p=1.0` | 应用 → 模型参数 → Top P 设为 `1.0` |
| `reasoning_effort` | 通过 **自定义模型参数** 传入（高级设置） |
| `max_tokens` | 应用 → 模型参数 → 最大 Token 数 |
| Function Call | Dify 自动转换为工具调用 |

### 传入 Hy3 专属参数

在 Dify 的模型供应商配置中，添加自定义参数：

```json
{
  "chat_template_kwargs": {
    "reasoning_effort": "high"
  }
}
```

## 端到端 Demo

### Demo 1：Hy3 驱动的技术文档助手（RAG 工作流）

**场景**：用 Hy3 构建一个回答内部技术文档问题的 ChatBot。

#### 工作流设计

```
[用户输入]
    │
    ▼
[知识库检索] ── 从上传的 markdown/pdf 文档中检索相关内容
    │
    ▼
[Hy3 LLM 节点] ── 基于检索结果 + 用户问题生成回答
    │
    ▼
[输出]
```

#### Dify 节点配置

**知识库检索节点**：
```
知识库：选择已上传的技术文档
检索设置：TopK=5, 相似度阈值=0.7
```

**Hy3 LLM 节点 Prompt**：

```
你是一个技术文档助手。请根据以下知识库检索结果回答用户问题。

**知识库内容**：
{{#context#}}

**用户问题**：
{{#query#}}

**回答要求**：
1. 优先使用知识库中的信息，不要编造
2. 如果知识库没有相关信息，明确告知用户
3. 如果涉及代码，使用 markdown 代码块格式
4. 回答要简洁、准确、有条理
```

#### 测试效果

```
用户：Hy3 的推理模式有哪些？
助手：根据文档，Hy3 支持三种推理模式，通过 reasoning_effort 参数控制：
- "no_think"：直接回复，适合日常对话
- "low"：轻度推理
- "high"：深度思维链，适合数学、编程等复杂任务
推荐在命令行中使用 temperature=0.9, top_p=1.0。
```

### Demo 2：Hy3 Agent —— 代码审查 + 自动创建 Issue

**工作流设计**：

```
[触发：GitHub Webhook]
    │
    ▼
[读取 PR 内容]
    │
    ▼
[Hy3 Agent 节点] ── 审查代码
    │           │
    │           └── [工具：GitHub API - 创建 Issue]
    │           └── [工具：GitHub API - 添加 Comment]
    │
    ▼
[条件分支] ── 审查通过？── Yes ──> [自动 Approve]
            │
            └── No ──> [创建 Issue + 通知]
```

**Hy3 Agent 系统 Prompt**：

```
你是一个代码审查 Agent。你的任务是：
1. 检查代码风格是否符合项目规范
2. 识别潜在的安全漏洞（SQL 注入、XSS 等）
3. 评估性能影响
4. 如果发现问题，使用 create_issue 工具创建 GitHub Issue
5. 使用 add_comment 工具在 PR 下添加审查意见

可用的工具：
- create_issue(title, body, labels)：创建 GitHub Issue
- add_comment(pr_number, body)：在 PR 下添加评论
- approve_pr(pr_number)：批准 PR
```

### Demo 3：批量内容生成流水线

**场景**：上传 CSV 关键词列表，Hy3 批量生成 SEO 文章。

```
[CSV 导入] ── 读取关键词列表
    │
    ▼
[迭代器] ── 逐条处理
    │
    ▼
[Hy3 LLM 节点]
    │  Prompt: "围绕关键词 {{keyword}} 写一篇 800 字的技术文章"
    ▼
[代码节点] ── 格式化 + 添加元数据
    │
    ▼
[输出：Markdown 文件列表]
```

## 常见注意事项

| 问题 | 原因 | 解决方案 |
|:---|:---|:---|
| 连接测试失败 | 网络不通或端点格式错误 | 确认 `base_url` 末尾是否带 `/v1` |
| Agent 工具调用失败 | Hy3 工具调用格式与 Dify 不兼容 | 确认 Hy3 服务部署时启用了 `--tool-call-parser hy_v3`（vLLM） |
| 知识库检索结果为空 | 文档未正确分段/索引 | 检查文档格式，调整分段参数 |
| 生成内容质量不稳定 | Temperature 参数不合适 | 内容生成类降到 `0.7-0.8`，创意类保持 `0.9` |
| `reasoning_effort` 不生效 | Dify 未传递自定义参数 | 在模型供应商配置中添加 `extra_body` 参数 |
| 工作流执行超时 | Hy3 Agent 推理耗时过长 | 增大 Dify 工作流超时时间，或使用 `reasoning_effort=low` |


[← 返回索引](../README.md)
