# 02 流式输出（Streaming）

这个示例会边接收边打印回答，并在结束时合并完整结果。完整代码见
[02_streaming.py](02_streaming.py)。

## 请求和解析

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

流式响应不保证每一块都有正文。`aggregate_stream` 会处理这些情况：

1. `choices=[]` 时不访问索引；如果该块含 `usage`，保存最终统计。
2. 分别拼接 `delta.reasoning_content` 与 `delta.content`。
3. 按 `tool_calls[].index` 拼接分片 arguments，不重复拼接 ID/name。
4. 保存非空 `finish_reason`；没有 finish reason 的流不标记为完整。
5. 迭代器抛错时抛出 `StreamInterruptedError`，其中只保留可识别的 partial result；
   部分文本不能当成完整答案。

## 运行结果

```powershell
python examples/api/02_streaming.py
```

以下输出采集于 2026-07-17，使用 TokenHub 广州入口、`model=hy3`、
`temperature=0.3` 和 `max_tokens=512`。开头几个 chunk 如下：

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

该次完整正文依次建议“打好基础”“多动手写代码”“围绕目标做项目”。chunk 怎样
切分由服务端决定，测试应检查合并后的文本、finish reason、usage 和 `complete`，
不要检查每个 chunk 的固定内容。

## 容易踩坑

- 只读取 `delta.content` 会漏掉 reasoning。
- 假设每一块都有 `choices`，会在只有 usage 的尾块报错。
- 网络中断后的部分文本不是完整答案，展示时要明确标记。
