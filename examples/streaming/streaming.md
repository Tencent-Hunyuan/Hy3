# 流式请求示例

## 功能说明

本示例演示如何使用 Hy3 API 的流式请求功能，实现逐 token 输出和实时响应。

## 前置条件

1. 安装依赖：`pip install openai python-dotenv`
2. 创建 `.env` 文件，配置 API 密钥：
   ```
   API_KEY=your_api_key
   BASE_URL=https://tokenhub.tencentmaas.com/v1
   ```

## 流式请求基础

### 请求参数

```python
stream = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "请用简短的语言介绍 Python 的主要特点"},
    ],
    temperature=0.9,
    top_p=1.0,
    stream=True,
)
```

关键参数：`stream=True` 启用流式输出

### Chunk 解析

流式响应返回一系列 chunk，每个 chunk 包含部分内容：

| 字段 | 说明 |
|:---|:---|
| `id` | 响应 ID（所有 chunk 相同） |
| `object` | 对象类型，通常为 `chat.completion.chunk` |
| `created` | 创建时间戳 |
| `model` | 使用的模型名称 |
| `choices[0].finish_reason` | 结束原因（最后一个 chunk 为 `stop`） |
| `choices[0].delta.role` | 角色（仅第一个 chunk 包含） |
| `choices[0].delta.content` | 新增内容片段 |

### 逐 Chunk 解析代码

```python
full_content = ""
finish_reason = None

for chunk in stream:
    if chunk.choices:
        delta = chunk.choices[0].delta
        if delta.content:
            full_content += delta.content
            print(delta.content, end="", flush=True)  # 实时输出
        if chunk.choices[0].finish_reason:
            finish_reason = chunk.choices[0].finish_reason
```

### 示例输出

```
--- Chunk #1 ---
  id: chatcmpl-xxx
  object: chat.completion.chunk
  created: 1715000000
  model: hy3
  choices[0]:
    finish_reason: None
    delta:
      ├─ role: assistant
      └─ content: 'Python'

--- Chunk #2 ---
  ...
  content: ' 是一种'
  ...
```

最终完整回复：

```
Assistant: Python 是一种简洁优雅的高级编程语言，具有丰富的库生态，支持多种编程范式，广泛应用于数据科学、Web 开发和人工智能领域。
```

## 流式请求 + 工具调用

### 请求参数

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市的天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称"},
                },
                "required": ["city"],
            },
        },
    }
]

stream = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "北京今天天气怎么样？"}],
    tools=tools,
    stream=True,
)
```

### 工具调用 Chunk 解析

```python
for chunk in stream:
    if chunk.choices:
        delta = chunk.choices[0].delta
        if delta.tool_calls:
            for tc in delta.tool_calls:
                print(f"  工具名: {tc.function.name}")
                print(f"  参数: {tc.function.arguments}")
```

### 示例输出

```
--- Chunk #1 ---
  delta.tool_calls:
    index: 0
    id: call_xxx
    type: function
    function:
      ├─ name: 'get_weather'
      └─ arguments: '{"city":"北京"}'
```

## 关键要点

1. **实时输出**：流式请求可以在响应生成过程中逐字显示，提升用户体验
2. **首 Token 时延**：用户可以更快看到第一个字符，减少等待感
3. **内存效率**：不需要等待完整响应，可以边接收边处理
4. **finish_reason**：通过检查 `finish_reason` 判断响应是否结束

## 运行方式

```bash
export API_KEY=your_api_key
export BASE_URL=https://tokenhub.tencentmaas.com/v1
python streaming.py
```