# Streaming — 流式请求与逐 chunk 解析

演示 `stream=True` 模式下的流式响应处理。流式请求不会等待完整生成结果，而是逐个 token 推送 delta 增量，适用于需要实时显示生成内容的场景（如聊天界面、代码补全）。

## 运行

```bash
cd issue1
python examples/streaming.py
```

## 请求结构

关键是设置 `stream=True`，其他参数与非流式一致：

```python
stream = client.chat.completions.create(
    model="hy3-preview",
    messages=[
        {"role": "user", "content": "请列出验证 Hy3 API 集成的 4 个关键步骤，每步一句话。"}
    ],
    temperature=0.7,
    top_p=1.0,
    max_tokens=256,
    stream=True,  # ← 关键
)
```

## 响应解析

流式返回的是一个**迭代器**，每个 `chunk` 的结构如下：

```python
for chunk in stream:
    if not chunk.choices:
        continue  # 某些 chunk 可能没有 choices

    choice = chunk.choices[0]
    delta = choice.delta          # 增量内容（非完整消息）
    finish_reason = choice.finish_reason

    # delta 中的关键字段
    role = delta.role             # 通常只在第一个 chunk 出现
    content = delta.content       # 增量文本，需自行拼接
    reasoning_content = delta.reasoning_content  # 思考内容（如有）
    tool_calls = delta.tool_calls # 工具调用增量（如有）
```

### chunk 特性

| 特性 | 说明 |
|:---|:---|
| `delta.role` | 通常只在**首个 chunk** 出现一次 |
| `delta.content` | `None` 或一小段文本，需要**手动拼接** |
| `delta.reasoning_content` | 仅在启用思考模式时出现，同样是增量 |
| `finish_reason` | 通常在**最后一个 chunk** 中出现 |
| `usage` | 大部分框架在流式模式下不返回 usage，需开启 `stream_options={"include_usage": True}` |

### 完整拼接示例

```python
content_parts = []
reasoning_parts = []

for chunk in stream:
    if not chunk.choices:
        continue
    delta = chunk.choices[0].delta
    if delta.content:
        content_parts.append(delta.content)
    if getattr(delta, "reasoning_content", None):
        reasoning_parts.append(delta.reasoning_content)

full_content = "".join(content_parts)
full_reasoning = "".join(reasoning_parts)
```

## 示例输出

以下为实际调用 TokenHub `hy3-preview` 的输出：

```
 chunk role         content                                  finish_reason
───── ──────────── ──────────────────────────────────────── ─────────────
    0 assistant    以下是                                    None
    1 None         验证                                      None
    2 None         Hy3                                       None
    3 None          API                                       None
    4 None         集成的                                    None
    5 None         四个                                      None
    6 None         关键                                      None
    7 None         步骤                                      None
    8 None         ：                                        None
    9 None

                                                        None
   10 None         1                                         None
   11 None         .                                         None
   12 None          认证                                      None
   13 None         与                                        None
   14 None         授权                                      None
  ...
   86 None         。                                        None
   87 None                                                   stop
───── ──────────── ──────────────────────────────────────── ─────────────

完整回复 (87 个 content chunk):
以下是验证 Hy3 API 集成的四个关键步骤：

1. **认证与授权**：确保 API Key 正确配置并能通过身份验证，使用简单的 echo 请求测试连通性。
2. **请求格式验证**：确认请求体 JSON 结构、字段名和数据类型完全符合 API 规范，处理必填和可选参数。
3. **响应解析测试**：验证能正确解析返回的 JSON 响应，包括正常回复、错误码和流式 chunk，确保异常路径也有处理。
4. **端到端集成验证**：在实际应用流程中运行完整测试，验证数据流、重试机制和速率限制处理均正常工作。
```

## 关键要点

1. **首字延迟**：流式请求的首 token 延迟显著低于非流式，交互体验更好
2. **Token 边界**：chunk 的 content 不一定按完整 token 分割，可能包含部分 UTF-8 字符
3. **错误处理**：流式过程中也可能抛出异常（网络断开等），需要 try/except
4. **内存管理**：对于超长生成，及时处理每个 chunk 而非全部缓存在内存中
