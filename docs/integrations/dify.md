# Hy3 with Dify

[Dify](https://dify.ai/) 是低代码 LLM 应用开发平台，支持接入 OpenAI 兼容模型。

## 1. 安装与版本要求

- 云端版：直接登录 https://dify.ai （无需安装）
- 私有部署：Docker Compose 或 Kubernetes，Dify ≥ 0.6
- 本地或云端已部署 Hy3 服务

## 2. 配置项

| 配置项 | 值 |
|--------|-----|
| 协议 | OpenAI-API-compatible |
| 模型类型 | `LLM` |
| Base URL | `http://127.0.0.1:8000/v1`（本地） |
| API Key | `EMPTY`（本地） |
| Model 名 | `hy3` |
| 配置入口 | 设置 → 模型供应商 → 添加 OpenAI-API-compatible |

## 3. 端到端流程

### 步骤 1：配置

1. Dify 控制台 → `设置` → `模型供应商`
2. 选择 `OpenAI-API-compatible`（或「添加模型」中搜索）
3. 填入：模型名称 `hy3`、Base URL、API Key、`LLM` 类型
4. 保存

### 步骤 2：第一次对话

创建一个 `Chatbot` 应用 → 编排页选 `hy3` → 输入「你好」验证连通。

### 步骤 3：跑通一个真实任务（Agent 工作流）

1. 新建 `Chatbot` → 选择 `Agent` 模式
2. 模型选 `hy3`，添加工具：计算器、网页搜索（Dify 内置）
3. 提示词：

```
你是一个智能助手。根据用户提问调用合适的工具回答问题，
无需工具时直接回答。
```

4. 发布并测试：「北京现在时间换算成纽约时间是几点？再算 123*456」

Hy3 会先调用计算器/时区工具，再综合给出答案。

## 4. 端到端 demo（截图 / GIF）

> 截图位置：见 [screenshots 指南 #7](../../screenshots/README.md#7-dify)
> - 图 1：Dify 模型供应商配置页
> - 图 2：Agent 应用编排页（已选 hy3）
> - 图 3：真实任务运行结果

## 5. 常见注意事项

- Dify 走 `/v1/chat/completions`，确认 Hy3 Base URL 正确且可访问
- Agent 模式依赖 tool calling，Hy3 需启用 `--enable-auto-tool-choice`
- 云端 Dify 只能连公网可达的 Hy3 地址
- Function Calling 用 OpenAI 标准 schema
- 知识库 embedding 需单独配置 embedding 模型，不影响对话
