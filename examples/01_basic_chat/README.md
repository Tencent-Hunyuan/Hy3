# Basic Chat (基础对话)

本示例展示了如何使用 Hy3 API 进行单轮和多轮对话。

## 1. 核心逻辑
- **单轮对话**：直接发送 `messages` 列表，不保留历史。
- **多轮对话**：关键在于维护 `messages` 列表。每次模型回复后，需将其回复内容 (`response.choices[0].message`) 追加到列表中，作为下一次请求的上下文。

## 2. 请求参数解析
- `model`: "hy3-preview" (指定使用的模型)
- `messages`: 对话历史数组。
  - `role`: "system" (设定角色), "user" (用户输入), "assistant" (模型回复)
  - `content`: 具体的文本内容
- `temperature`: 0.5 (控制随机性，越低越稳定)

## 3. 响应解析 (Response Parsing)
以单轮对话为例，核心返回值结构如下：
- `response.choices[0].message.role`: "assistant"
- `response.choices[0].message.content`: 模型生成的文本内容
- `response.usage.prompt_tokens`: 输入消耗的 Token 数
- `response.usage.completion_tokens`: 输出消耗的 Token 数

## 4. 运行示例输出

模型回复：腾讯混元大模型是腾讯自主研发的千亿级参数规模大模型，具备强大的多模态理解与生成能力，覆盖文本、图像、视频等多种内容形式。它深度融合了行业知识图谱与实时数据，在逻辑推理、代码生成、长文本处理等任务中表现突出，可广泛应用于智能客服、内容创作、办公协同等场景。目前，混元已通过腾讯云对外开放API服务，并持续迭代优化，致力于为企业和个人提供安全、高效、易用的AI解决方案。
Token消耗：输入23，输出101，总124

