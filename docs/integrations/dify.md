# Hy3 with Dify

[Dify](https://dify.ai/) 是一个低代码 LLM 应用开发平台，支持接入 OpenAI 兼容的模型。

## 配置

### 添加模型供应商

1. 登录 Dify 控制台 → 设置 → 模型供应商
2. 选择 **OpenAI-API-compatible**（如果列表中没有，在 "添加模型" 中搜索）
3. 填入以下配置：

| 配置项 | 值 |
|--------|-----|
| 模型名称 | `hy3` |
| Base URL | `http://127.0.0.1:8000/v1` |
| API Key | `EMPTY`（本地） |
| 模型类型 | `LLM` |

### 在应用中使用

1. 创建一个新的 Text Generator App 或 Chatbot App
2. 在编排页面选择 `hy3` 作为模型
3. 配置参数：

| 参数 | 建议值 |
|------|--------|
| Temperature | 0.7 ~ 0.9 |
| Max Tokens | 4096 |
| Top P | 1.0 |

## 功能支持

| Dify 功能 | 支持情况 |
|-----------|----------|
| Chatbot App | ✅ |
| Text Generator | ✅ |
| Agent（工具调用） | ✅ |
| Workflow | ✅ |
| 知识库 | ✅（仅 embedding 需额外配置） |
| 变量/提示词模板 | ✅ |

## 示例：创建一个 Agent App

1. 创建 **Chatbot** → 选择 **Agent** 模式
2. 选择模型 `hy3`
3. 添加工具（如计算器、天气查询等 Dify 内置工具）
4. 在提示词中加入：

```
你是一个智能助手。请根据用户的提问，调用合适的工具来回答问题。
如果不需要工具，直接回答即可。
```

5. 发布并测试

## 注意事项

- Dify 默认通过 `/v1/chat/completions` 路径请求，确保 Hy3 的 base URL 正确
- Agent 模式依赖 tool calling，需要 Hy3 启用 `--enable-auto-tool-choice`
- 如果使用 Dify 云端版，只能连接公开可访问的 Hy3 地址
- Function Calling 的参数格式请使用 OpenAI 标准格式

## 截图

> 待补充：Dify 模型配置截图 + Agent App 运行截图
