# 基础聊天示例

## 功能说明

本示例演示如何使用 Hy3 API 进行单轮和多轮对话。

## 前置条件

1. 安装依赖：`pip install openai python-dotenv`
2. 创建 `.env` 文件，配置 API 密钥：
   ```
   API_KEY=your_api_key
   BASE_URL=https://tokenhub.tencentmaas.com/v1
   ```

## 单轮对话

### 请求参数

```python
response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "你好！请简单介绍一下你自己。"},
    ],
    temperature=0.9,
    top_p=1.0,
    "reasoning_effort": "low",
)
```

### Response 解析

| 字段 | 说明 |
|:---|:---|
| `id` | 响应 ID |
| `object` | 对象类型，通常为 `chat.completion` |
| `created` | 创建时间戳 |
| `model` | 使用的模型名称 |
| `choices` | 选择列表，包含生成的回复 |
| `choices[0].finish_reason` | 结束原因（`stop` 表示正常结束） |
| `choices[0].message.role` | 角色（`assistant`） |
| `choices[0].message.content` | 回复内容 |
| `usage.prompt_tokens` | 输入 token 数 |
| `usage.completion_tokens` | 输出 token 数 |
| `usage.total_tokens` | 总 token 数 |

### 示例输出

```
Assistant: 你好！我是 Hy3，是腾讯混元团队研发的大语言模型。我具备强大的推理能力和工具调用能力，支持长上下文对话。
```

## 多轮对话

### 实现方式

多轮对话需要维护 `messages` 数组，每次请求时传入完整的对话历史：

```python
messages = []

# 第一轮
messages.append({"role": "user", "content": "什么是 MoE 模型？"})
response = client.chat.completions.create(model="hy3", messages=messages, ...)
messages.append({"role": "assistant", "content": response.choices[0].message.content})

# 第二轮
messages.append({"role": "user", "content": "Hy3 在 MoE 架构上有什么创新？"})
response = client.chat.completions.create(model="hy3", messages=messages, ...)
```

### 关键要点

1. **维护完整历史**：每次请求必须包含所有历史消息
2. **角色顺序**：`user` 和 `assistant` 交替出现
3. **上下文限制**：总 token 数不能超过模型限制（256k）

### 示例输出

```
User: 什么是 MoE 模型？

Assistant: **MoE（Mixture of Experts，混合专家模型）** 是一种神经网络架构，核心思想是**将大模型拆分成多个专门处理不同任务的“专家”子网络，并通过一个...

User: Hy3 在 MoE 架构上有什么创新？

Assistant: 您提到的“Hy3”很可能是指**腾讯混元大模型（Hunyuan）的 MoE 版本...

【多轮请求的关键参数】
  messages 数组长度: 3
  历史对话包含: 2 次用户提问
  最后一轮请求的 messages:
    [0] user: 什么是 MoE 模型？...
    [1] assistant: **MoE（Mixture of Experts，混合专家模型）** 是一种神经网络架构，核心思想是...
    [2] user: Hy3 在 MoE 架构上有什么创新？...
```

## 运行方式

```bash
# 使用环境变量
export API_KEY=your_api_key
export BASE_URL=https://tokenhub.tencentmaas.com/v1
python basic_chat.py

# 或使用 .env 文件
pip install python-dotenv
echo "API_KEY=your_api_key" > .env
echo "BASE_URL=https://tokenhub.tencentmaas.com/v1" >> .env
python basic_chat.py
```