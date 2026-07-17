# 02 — Streaming

目标：逐 chunk 解析流式响应，并正确处理 reasoning/content 分流、空 `choices`、
usage-only 尾块、finish reason 和中断后的部分输出。完整代码见
[02_streaming.py](02_streaming.py)。

## 完整请求与解析

```python
stream = create_chat_completion(
    client,
    model=config.model,
    messages=[{"role": "user", "content": "列出三个学习 Python 的建议。"}],
    temperature=0.3,
    max_tokens=512,
    stream=True,
    stream_options={"include_usage": True},
    extra_body={"thinking": {"type": "disabled"}},
)
result = aggregate_stream(stream, on_content=print, on_reasoning=print)
```

共享聚合器执行以下边界处理：

1. `choices=[]` 时不访问索引；如果该块含 `usage`，保存最终统计。
2. 分别拼接 `delta.reasoning_content` 与 `delta.content`。
3. 按 `tool_calls[].index` 拼接分片 arguments，不重复拼接 ID/name。
4. 保存非空 `finish_reason`；没有 finish reason 的流不标记为完整。
5. 迭代器抛错时抛出 `StreamInterruptedError`，其中只保留可识别的 partial result；
   部分文本不能当成完整答案。

## 运行与真实输出

```powershell
python examples/api/02_streaming.py
```

2026-07-17 在 TokenHub 广州入口以 `model=hy3`、`temperature=0.3`、
`max_tokens=512` 实测通过。真实 chunk 开头如下：

```text
content delta: '以下是'
content delta: '三个'
content delta: '学习 Python '
content delta: '的实用建议'
content delta: '：'
content delta: '\n\n1.'
```

同一次请求聚合后得到：

```text
content 开头：以下是三个学习 Python 的实用建议：
reasoning_content：""
tool_calls：[]
finish_reason：stop
usage：completion_tokens=202, prompt_tokens=22, total_tokens=224
complete：true
```

该次完整正文依次建议“打好基础”“多动手写代码”“围绕目标做项目”。chunk 边界由
服务端每次动态决定，不应写测试去断言上述切分；应断言聚合后的文本、finish reason、
usage 和 `complete`。

常见错误：只读取 `delta.content` 会丢失 reasoning；假设每块都有 choices 会在 usage
尾块崩溃；网络中断后直接展示已有文本会误导用户认为回答已完成。
