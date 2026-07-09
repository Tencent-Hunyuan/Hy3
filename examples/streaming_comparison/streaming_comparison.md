# 非流式 vs 流式对比示例

## 功能说明

本示例对比非流式（同步）和流式（异步）两种请求方式的性能差异，重点关注首 Token 时延（TTFT）和总耗时。

## 前置条件

1. 安装依赖：`pip install openai python-dotenv`
2. 创建 `.env` 文件，配置 API 密钥：
   ```
   API_KEY=your_api_key
    BASE_URL=https://tokenhub.tencentmaas.com/v1
   ```

## 性能指标

| 指标 | 说明 |
|:---|:---|
| **TTFT** (Time To First Token) | 从请求开始到收到第一个 token 的时间 |
| **Total Time** | 从请求开始到收到完整响应的时间 |
| **Content Length** | 响应内容的字符长度 |


## 非流式请求

### 请求代码

```python
import time

start_time = time.time()

response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "请详细解释什么是人工智能大模型"},
    ],
    temperature=0.9,
    top_p=1.0,
)

total_time = time.time() - start_time
content = response.choices[0].message.content
```

### 特点

- **同步阻塞**：等待完整响应生成后才返回
- **TTFT = Total Time**：用户必须等待全部内容生成
- **简单直接**：代码逻辑简单，适合批量处理

## 流式请求

### 请求代码

```python
import time

start_time = time.time()
first_token_time = None

stream = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "请详细解释什么是人工智能大模型"},
    ],
    temperature=0.9,
    top_p=1.0,
    stream=True,
)

full_content = ""
for chunk in stream:
    if chunk.choices and chunk.choices[0].delta.content:
        if first_token_time is None:
            first_token_time = time.time() - start_time
        full_content += chunk.choices[0].delta.content

total_time = time.time() - start_time
```

### 特点

- **异步流式**：响应生成过程中逐块返回
- **TTFT < Total Time**：用户可以更快看到第一个字符
- **实时体验**：提升用户感知的响应速度

## 关键结论

1. **TTFT 优势**：流式请求的首 Token 时延通常比非流式低 80-90%
2. **总耗时相近**：两种方式的总耗时差异不大
3. **用户体验**：流式能让用户更早看到内容，减少等待焦虑
4. **适用场景**：
   - **流式**：实时对话、聊天界面、需要快速响应的场景
   - **非流式**：批量处理、后台任务、需要完整响应的场景

## 运行方式

```bash
export API_KEY=your_api_key
export BASE_URL=https://tokenhub.tencentmaas.com/v1
python streaming_comparison.py
```

## 示例输出

```
=== Non-Streaming vs Streaming 对比测试 ===

测试问题: 请详细解释什么是人工智能大模型
============================================================

=== 非流式请求 ===

=== 流式请求 ===

============================================================
【性能对比结果】
------------------------------------------------------------
指标                      非流式           流式
------------------------------------------------------------
首 Token 时延 (TTFT)         33.8366s 0.7273s
总耗时 (Total Time)          33.8366s 11.9818s
内容长度                      1499            1544 
------------------------------------------------------------

首 Token 时延提升: 97.9%

【示例输出（截断）】

非流式回复:
  人工智能大模型是指参数量巨大、能够处理复杂任务的深度学习模型...

流式回复:
  人工智能大模型是指参数量巨大、能够处理复杂任务的深度学习模型...

【关键结论】
1. 非流式: 需要等待完整响应生成后才能获取结果
2. 流式: 可以快速获取第一个 token，提升用户体验
3. 首 Token 时延是流式最大优势，适合实时对话场景
4. 总耗时两者相近，但流式能让用户更早看到内容
```