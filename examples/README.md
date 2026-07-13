# Hy3 API 使用示例

本目录包含 Hy3 API 的完整使用示例，涵盖基础聊天、流式请求、工具调用、推理模式和错误处理等场景。

## 环境准备

### 安装依赖

```bash
pip install openai python-dotenv
```

### 配置环境变量

创建 `.env` 文件，配置 API 密钥：

```env
API_KEY=your_api_key
BASE_URL=https://tokenhub.tencentmaas.com/v1
```

或者直接设置环境变量：

```bash
export API_KEY=your_api_key
export BASE_URL=https://tokenhub.tencentmaas.com/v1
```

## API 基础信息

### Base URL

```
https://tokenhub.tencentmaas.com/v1
```

### Model 名称

| 模型 | 模型名 | 说明 |
|:---|:---|:---|
| Hy3 | `hy3` | Hy3 基于真实业务场景打磨，兼具效果和性价比，强化 Coding、长文、推理和 Agent 等能力。 |
| Hy3-preview | `hy3-preview` | Hy3 Preview 面向 Agent 工作负载设计，采用 MoE 架构。 |

### 速率限制

| 限制项 | 数值 |
|:---|:---|
| 最大 QPM（每分钟请求数） | 60 |
| 最大 TPM（每分钟 tokens 数） | 1,000,000 |
| 最大输入 Tokens | 192k |
| 最大输出 Tokens | 128k |
| 上下文窗口 | 256k |

## 快速开始

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://tokenhub.tencentmaas.com/v1",
    api_key="YOUR_API_KEY"
)

response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "你好！请简单介绍一下你自己。"}
    ],
    temperature=0.9,
    top_p=1.0,
    extra_body={"reasoning_effort": "low"},
)

print(response.choices[0].message.content)
```

## 核心参数说明

### temperature

控制输出的随机性。

- **范围**: 0.0 ~ 2.0
- **推荐**: `0.9`
- **说明**: 低数值输出更确定，高数值输出更多样

### top_p

核采样参数，控制累积概率阈值。

- **范围**: 0.0 ~ 1.0
- **推荐**: `1.0`

### reasoning_effort

控制推理深度。

| 模式 | 参数值 | 适用场景 |
|:---|:---|:---|
| 直接回复 | `"low"` | 轻量推理，速度快，适合简单任务（默认） |
| 轻度思考 | `"medium"` | 平衡模式，适合大多数日常任务 |
| 深度思维链 | `"high"` | 深度推理，适合高难度数学、编程或复杂逻辑推理 |

### thinking

思考模式开关。

```python
# 开启深度思考
extra_body={"thinking": {"type": "enabled"}}

# 关闭深度思考（默认）
extra_body={"thinking": {"type": "disabled"}}
```

### stream

流式输出开关。

- **默认**: `false`
- **说明**: 设置为 `true` 时，响应会以 SSE 流式返回

## 示例导航

| 示例 | 功能说明 | 文件 |
|:---|:---|:---|
| [基础聊天](basic_chat/) | 单轮和多轮对话 | `basic_chat.py` |
| [流式请求](streaming/) | 逐 token 实时输出 | `streaming.py` |
| [非流式 vs 流式对比](streaming_comparison/) | 两种请求方式性能对比 | `streaming_comparison.py` |
| [工具调用](tool_calling/) | 单次工具调用和多轮工具循环 | `tool_calling.py` |
| [推理模式](reasoning_mode/) | 不同推理深度对比 | `reasoning_mode.py` |
| [错误处理](error_handling/) | 超时、限流、网络错误的重试策略 | `error_handling.py` |

## 运行示例

```bash
# 进入对应目录
cd basic_chat

# 设置环境变量
export API_KEY=your_api_key
export BASE_URL=https://tokenhub.tencentmaas.com/v1

# 运行示例
python basic_chat.py
```

## 常见问题

### Q: 输出包含 `<think>` 标签？

**解决**：通过 `extra_body={"thinking": {"type": "disabled"}}` 禁用思考模式。

### Q: 工具调用格式错误？

**解决**：确保 tools 数组中每个元素包含 `type: "function"` 和 `function` 对象，`function` 对象必须包含 `name`、`description` 和 `parameters`。

### Q: 请求被限流？

**解决**：等待一段时间后重试，优化请求频率，避免短时间内大量请求。

### Q: API Key 无效？

**解决**：检查 API Key 是否正确，确保 Authorization header 格式为 `Bearer YOUR_API_KEY`。

## 参考文档

- [快速入门](../quickstart.md) - 完整的 API 参考文档
- [官方文档](https://aistudio.tencent.com/) - Hy3 官方网站
