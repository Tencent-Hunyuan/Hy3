<p align="left">
    <a href="../05_reasoning_mode.md">English</a>&nbsp;｜&nbsp;中文
</p>
<br>

# 示例 05：推理模式

本示例对比 `reasoning_effort="no_think"` 和 `reasoning_effort="high"`。

> 相关文档：[示例索引](./README.md) | [API 快速开始](../../quickstart_CN.md)

## 运行

```bash
python examples/zh-cn/05_reasoning_mode.py
```

## 完整请求

```python
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "一个水池有进水管和出水管..."}],
    temperature=0.2,
    max_tokens=900,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}},
)
```

等价的 HTTP 请求体：

```json
{
  "model": "hy3",
  "messages": [
    {"role": "user", "content": "一个水池有进水管和出水管。进水管 6 小时注满，出水管 9 小时放空。两管同时开，多久注满？请给出答案。"}
  ],
  "temperature": 0.2,
  "max_tokens": 900,
  "chat_template_kwargs": {"reasoning_effort": "high"}
}
```

## 响应解析

```python
message = response.choices[0].message
answer = message.content
reasoning_content = getattr(message, "reasoning_content", None)
```

如果缺少 `reasoning_content`，说明服务端可能没有启用 reasoning parser，或者框架没有单独暴露推理内容。

## 示例输出

```text
=== reasoning_effort=no_think ===
耗时_s: 1.942
答案:
两管同时开时，净注水速度为 1/6 - 1/9 = 1/18 个水池/小时，因此 18 小时注满。
检测到 reasoning_content: 否
用量: CompletionUsage(...)

=== reasoning_effort=high ===
耗时_s: 4.815
答案:
答案是 18 小时。进水管每小时注入 1/6 个水池，出水管每小时放出 1/9 个水池，净速度为 1/18 个水池/小时，所以注满需要 18 小时。
检测到 reasoning_content: 是
推理预览: [文档中省略/截断了 reasoning content] ...
用量: CompletionUsage(...)
```
