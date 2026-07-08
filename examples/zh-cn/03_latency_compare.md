<p align="left">
    <a href="../03_latency_compare.md">English</a>&nbsp;｜&nbsp;中文
</p>
<br>

# 示例 03：非流式与流式延迟对比

本示例对比普通请求的总延迟，以及流式请求的首 token 延迟和总延迟。

> 相关文档：[示例索引](./README.md) | [API 快速开始](../../quickstart_CN.md)

## 运行

```bash
python examples/zh-cn/03_latency_compare.py
```

## 完整请求

非流式：

```python
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "请写一段约 300 字的说明..."}],
    temperature=0.7,
    top_p=1.0,
    max_tokens=700,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)
```

流式：

```python
stream = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "请写一段约 300 字的说明..."}],
    temperature=0.7,
    top_p=1.0,
    max_tokens=700,
    stream=True,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)
```

## 响应解析

```python
text = response.choices[0].message.content

first_token_time = None
for chunk in stream:
    content = getattr(chunk.choices[0].delta, "content", None)
    if content and first_token_time is None:
        first_token_time = time.perf_counter() - start
```

## 示例输出

```text
=== 延迟对比 ===
非流式总耗时_s: 8.214
流式首token耗时_s: 0.732
流式总耗时_s: 8.046
非流式字符数: 348
流式字符数: 352
```

解读：流式输出通常不会减少总生成时间，但可以降低感知延迟，因为用户能更早看到第一个 token。
