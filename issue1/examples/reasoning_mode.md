# Reasoning Mode — 思考模式对比

Hy3 的核心特性之一是**快慢思考融合**推理。通过 `reasoning_effort` 参数可以在「直接回答」和「深度思维链推理」之间切换。本文档对比两种模式的差异。

## 运行

```bash
cd issue1
python examples/reasoning_mode.py
```

## 思考模式级别

| effort | 含义 | 适用场景 | 延迟 | Token 消耗 |
|:---|:---|:---|:---|:---|
| `no_think` | 跳过思考，直接回答 | 日常对话、信息检索、简单翻译 | 最低 | 最少 |
| `low` | 简短内部推理 | 中等难度推理、格式化输出 | 中等 | 较多 |
| `high` | 完整深度思维链 | 数学证明、复杂编程、多步规划 | 最高 | 最多 |

## 请求结构

### 本地部署（vLLM/SGLang）

本地部署时通过 `chat_template_kwargs` 传递思考模式参数：

```python
# 关闭思考 — 直接回答
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "..."}],
    temperature=0.2,
    max_tokens=512,
    extra_body={
        "chat_template_kwargs": {"reasoning_effort": "no_think"}
    },
)

# 开启深度思考
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "..."}],
    temperature=0.2,
    max_tokens=512,
    extra_body={
        "chat_template_kwargs": {"reasoning_effort": "high"}
    },
)
```

### TokenHub 云端 API

云端 API 使用标准 OpenAI 协议，**不支持 `chat_template_kwargs`**。Hy3 模型本身具备推理能力，模型会根据问题复杂度自然展现推理行为。如需完整的 reasoning_content 暴露，请使用本地部署。

## 响应解析

```python
choice = response.choices[0]
message = choice.message

# 兼容获取推理内容（不同服务可能用不同字段名）
reasoning = (
    getattr(message, "reasoning_content", None) or
    getattr(message, "reasoning", None) or
    getattr(message, "reasoning_details", None)
)

# 最终回答
answer = message.content

# Token 用量（推理模式通常消耗更多 completion_tokens）
usage = response.usage
```

> ⚠️ `reasoning_content` 字段是否暴露取决于服务端配置。生产代码中始终使用 `getattr` 兼容处理。

## 示例输出

以下为实际调用 TokenHub `hy3-preview` 的输出：

```
============================================================
【思考模式: no_think（直接回答）】
============================================================
问题: 一个房间里有 5 个人。每个人和其他所有人都握了一次手。请问总共发生了多少次握手？请逐步推理。

耗时:           2.147s
完成原因:       stop
reasoning_content: 无（云端 API 未暴露）
回答:  
这是一个经典的握手问题，可以用组合数学来解决。

**逐步推理：**

1. **理解题意**：每个人和除自己以外的其他所有人都握了一次手，即每两个人之间恰好握一次手（无重复）。

2. **抽象为组合问题**：从 5 个人中任选 2 人握一次手，握手的次数等于 5 人选 2 人的组合数。

3. **计算**：C(5,2) = 5! / (2! × 3!) = (5 × 4) / (2 × 1) = 10

4. **验证**：也可用等差数列验证：第一个人和其余 4 人握手，第二个人再和剩余 3 人握手…… 4 + 3 + 2 + 1 + 0 = 10。

**答案**：总共发生了 **10 次** 握手。

Token 用量: 输入=45, 输出=227, 总计=272
```

## 关键要点

1. **何时用 high**：数学题、逻辑推理、代码调试、复杂决策——有明确「对错」的任务
2. **何时用 no_think**：闲聊、翻译、摘要、信息提取——无需多步推理的任务
3. **Token 成本**：`high` 模式下思考 token 会计入 `completion_tokens`，增加成本
4. **延迟权衡**：`high` 模式生成更多 token，延迟显著增加。交互式场景需权衡体验
5. **云端限制**：TokenHub 云端目前不暴露 `reasoning_content`，但模型内部仍执行推理；完整思考过程需本地部署
