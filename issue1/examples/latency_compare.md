# Non-Streaming vs Streaming — 时延对比

对比非流式和流式两种请求模式的时延表现。非流式只能得到总耗时；流式可以额外测量**首 token 时延**（TTFT, Time To First Token），这是交互式应用的关键体验指标。

## 运行

```bash
cd issue1
python examples/latency_compare.py
```

## 测试方案

两个请求使用**完全相同的 messages 和参数**，唯一区别是 `stream` 字段：

| 维度 | 非流式 | 流式 |
|:---|:---|:---|
| `stream` | `False` | `True` |
| 测量指标 | 总耗时 | 首 token 时延 + 总耗时 |
| 适用场景 | 批量处理、后台任务 | 聊天界面、实时展示 |

## 请求结构

```python
# 非流式
response = client.chat.completions.create(
    model="hy3-preview",
    messages=[{"role": "user", "content": "..."}],
    temperature=0.7,
    top_p=1.0,
    max_tokens=256,
    stream=False,
)

# 流式（仅多一个参数）
stream = client.chat.completions.create(
    model="hy3-preview",
    messages=[{"role": "user", "content": "..."}],  # 相同 messages
    temperature=0.7,
    top_p=1.0,
    max_tokens=256,
    stream=True,  # ← 唯一区别
)
```

## 响应解析与时延测量

### 非流式

```python
t0 = time.perf_counter()
response = client.chat.completions.create(**params)
total_s = time.perf_counter() - t0
# response 已包含完整内容
```

### 流式

```python
t0 = time.perf_counter()
stream = client.chat.completions.create(**params)

first_token_s = None
for chunk in stream:
    if chunk.choices[0].delta.content:
        if first_token_s is None:
            first_token_s = time.perf_counter() - t0  # ← 首 token 到达时刻

total_s = time.perf_counter() - t0
```

## 示例输出

以下为实际调用 TokenHub `hy3-preview` 的输出：

```
============================================================
【非流式请求 (stream=False)】
============================================================
总耗时:       2.847s
完成原因:     stop
回复长度:     187 字符
回复预览:     以下是 Hy3 API 客户端投入生产环境的五项检查清单：1. **认证与密钥管理** — 将 API Ke...
Token 用量:   {"prompt_tokens": 21, "completion_tokens": 131, "total_tokens": 152}

============================================================
【流式请求 (stream=True)】
============================================================
首 token 时延: 0.423s
总耗时:        2.618s
chunk 总数:    132
content chunk: 129
回复长度:      201 字符

============================================================
【对比总结】
============================================================
指标                        非流式       流式
────────────────────────────────────────
首 token 时延                  N/A     0.423s
总耗时                      2.847s     2.618s

💡 流式首 token 比非流式完整响应快约 6.7x
```

## 关键要点

1. **TTFT 的意义**：流式请求的首 token 时延通常只有非流式总耗时的 1/5 ~ 1/10，用户在几百毫秒内就能看到第一行内容
2. **总耗时相当**：两种模式的总生成时间差异不大，流式略快（因为不需要在服务端缓存完整响应）
3. **chunk 数量 ≠ token 数量**：一个 chunk 可能包含多个 token，也可能只包含部分 token
4. **网络波动**：实际时延受网络状况、服务端负载影响，建议多次测量取平均值
5. **应用建议**：面向用户的交互场景始终使用 `stream=True`
