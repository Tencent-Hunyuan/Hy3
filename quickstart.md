# Hy3 API 快速入门

## 基础信息

### Base URL

```
https://tokenhub.tencentmaas.com/v1
```

### API Key

在腾讯云控制台申请 API Key：

```
Bearer sk-xxx
```

> 申请地址：[腾讯云控制台 - TokenHub](https://console.cloud.tencent.com/tokenhub/models)

### Model 名称

| 模型 | 模型名 | 说明 |
|:---|:---|:---|
| Hy3 | `hy3` | Hy3 基于真实业务场景打磨，兼具效果和性价比，强化 Coding、长文、推理和 Agent 等能力。 |
| Hy3-preview | `hy3-preview` | Hy3 Preview 面向 Agent 工作负载设计，采用 MoE 架构，支持交错式思考、结构化输出、Function Calling、Cache 缓存。 |

### 速率限制

| 限制项 | 数值 |
|:---|:---|
| 最大 QPM（每分钟请求数） | 60 |
| 最大 TPM（每分钟 tokens 数） | 1,000,000 |
| 最大输入 Tokens | 192k |
| 最大输出 Tokens | 128k |
| 上下文窗口 | 256k |

---

## 最小可运行示例

### cURL	

Git Bash / WSL / Linux 

```bash
curl -X POST https://tokenhub.tencentmaas.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "model": "hy3",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "你好"}
    ],
    "stream": false
  }'
```

Windows CMD

```powershell
curl -X POST https://tokenhub.tencentmaas.com/v1/chat/completions -H "Content-Type: application/json" -H "Authorization: Bearer YOUR_API_KEY" -d "{\"model\":\"hy3\",\"messages\":[{\"role\":\"system\",\"content\":\"You are a helpful assistant.\"},{\"role\":\"user\",\"content\":\"你好\"}],\"stream\":false}"
```

### Python OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://tokenhub.tencentmaas.com/v1",
    api_key="YOUR_API_KEY"
)

response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "你好"}
    ],
    stream=False
)

print(response.choices[0].message.content)
```

---

## 参数说明

### temperature

控制输出的随机性。

- **范围**: 0.0 ~ 2.0
- **推荐**: `0.9`
- **说明**:
  - 低数值（接近 0）：输出更确定、更保守
  - 高数值（接近 2）：输出更多样、更具创造性

### top_p

核采样参数，控制累积概率阈值。

- **范围**: 0.0 ~ 1.0
- **推荐**: `1.0`
- **说明**:
  - 只从概率累积和达到 top_p 的 token 中采样
  - 通常不需要同时调整 temperature 和 top_p

### max_tokens

限制生成的最大 token 数。

- **范围**: 1 ~ 128000
- **说明**:
  - 最大输出为 128k tokens
  - 输入 + 输出总长度不超过 256k

### stop

停止序列。

```python
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "请列举三个水果。"}],
    stop=["。"]
)
```

- **说明**: 当生成到 stop 序列时，生成会立即停止
- **支持**: 字符串或字符串数组

### tools

工具调用配置。

```python
response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "今天北京天气怎么样？"}
    ],
    tools=[{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市的天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称"}
                },
                "required": ["city"]
            }
        }
    }],
    tool_choice="auto"
)

if response.choices[0].message.tool_calls:
    tool_call = response.choices[0].message.tool_calls[0]
    print(f"工具名: {tool_call.function.name}")
    print(f"参数: {tool_call.function.arguments}")
```

### 思考模式开关

控制模型是否进行深度推理。

默认值：disabled

```python
#通过 thinking 参数控制是否开启思考模式。
#开启深度思考：
extra_body={"thinking": {"type": "enabled"}},
#关闭深度思考：
extra_body={"thinking": {"type": "disabled"}},
```

### 推理深度配置

默认值：low

```python
response = client.chat.completions.create(
    model="hy3",
    messages=[        
{"role": "user", "content": "解方程：2x+5=15"},    
],
    temperature=0.9,
    extra_body={"reasoning_effort": "high"},
)
```

| 模式 | 参数值 | 适用场景 |
|:---|:---|:---|
| 直接回复 | `"low"` | 轻量推理，推理步数少，速度快，适合简单任务。 |
| 轻度思考 | `"medium"` | 平衡模式，适合大多数日常、逻辑适中的复杂任务。 |
| 深度思维链 | `"high"` | 深度推理，推理时间最长，思考最深入，适合高难度数学、编程或复杂逻辑推理任务，但延迟和成本最高。 |

### stream

流式输出开关。

- **默认**: `false`
- **说明**: 设置为 `true` 时，响应会以 SSE（Server-Sent Events）流式返回
- 如需在最后一个 chunk 拿到完整 `usage` 统计，请加 `stream_options: { "include_usage": true }`。

---

## 常见报错排查

### 404 Not Found

**原因**: API 端点不正确

**解决**:
- 确认 URL 完整路径为 `https://tokenhub.tencentmaas.com/v1/chat/completions`

### 401 Unauthorized

**原因**: API Key 无效或缺失

**解决**:
- 检查 API Key 是否正确
- 确保 Authorization header 格式为 `Bearer YOUR_API_KEY`

### 429 Too Many Requests

**原因**: 超过速率限制（QPM 或 TPM）

**解决**:
- 等待一段时间后重试
- 优化请求频率，避免短时间内大量请求

### 500 Internal Server Error

**原因**: 服务端内部错误

**解决**:
- 稍后重试
- 持续失败请联系腾讯云客服

### 输出包含 `<think>` 标签

**原因**: 思考模式未正确关闭

**错误做法**:
```python
# ❌ 错误：用 stop 无法正确禁用思考
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "问题"}],
    stop=["<think>"]
)
```

**正确做法**:
```python
# ✅ 正确：通过 extra_body 禁用思考
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "问题"}],
    extra_body={"thinking": {"type": "disabled"}},
)
```

### 工具调用格式错误

**原因**: tools 参数格式不符合规范

**解决**:
- 确保 tools 数组中每个元素包含 `type: "function"` 和 `function` 对象
- function 对象必须包含 `name`、`description` 和 `parameters`
- parameters 必须符合 JSON Schema 格式

### 请求超时

**原因**: 网络问题或模型推理耗时过长

**解决**:
- 增加 timeout 参数
- 简化请求，减少输入长度

---

## 完整示例

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://tokenhub.tencentmaas.com/v1",
    api_key="YOUR_API_KEY"
)

response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "system", "content": "你是一个专业的编程助手。"},
        {"role": "user", "content": "请用 Python 实现快速排序算法。"}
    ],
    temperature=0.7,
    top_p=0.9,
    max_tokens=2000,
    stop=["\n\n"],
    stream=False,
    extra_body={"reasoning_effort": "high"},
)

print(response.choices[0].message.content)
```