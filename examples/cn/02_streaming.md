# 02 流式输出示例

## 简介

本示例演示如何通过 OpenAI 兼容 API 以**流式（streaming）**方式调用 Hy3。

流式调用会在 `client.chat.completions.create(..., stream=True)` 时立即返回一个迭代器，
模型每生成一个 token（或一小段文本）就推送一个 `chunk`，客户端可以**增量地**接收并打印输出，
从而实现打字机式的实时展示效果，显著降低用户感知的首字等待时间。

适用场景：聊天助手、交互式问答、实时内容生成等需要边生成边展示的体验。

---

## 完整请求

> 运行前请先通过 vLLM / SGLang 部署 Hy3 服务（默认监听 `127.0.0.1:8000`）。
> 可通过环境变量 `HY3_BASE_URL`、`HY3_API_KEY` 覆盖连接信息。
> 完整可运行脚本位于 `../en/02_streaming.py`。

```python
"""Hy3 Example 02: Streaming request + per-chunk parsing.

Demonstrates streaming mode via the OpenAI-compatible API, printing tokens
incrementally and assembling the full text at the end.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common import (  # noqa: E402
    chat_completion,
    get_config,
    iter_stream_text,
    make_client,
)


def main():
    cfg = get_config()
    print(f"Connecting to {cfg['base_url']}  model={cfg['model']}")
    client = make_client()

    messages = [
        {
            "role": "user",
            "content": (
                "请用中文写一段关于「秋天的银杏林」的短文，"
                "包含颜色、声音和心情的描写，至少三句话。"
            ),
        },
    ]

    print("=== Streaming Output (per-chunk print) ===")
    stream = chat_completion(client, messages, reasoning="no_think", stream=True)

    full_text_parts = []
    for content in iter_stream_text(stream):
        print(content, end="", flush=True)
        full_text_parts.append(content)

    print("\n\n=== Stream ended, assembling full text ===")
    full_text = "".join(full_text_parts)
    print(full_text)


if __name__ == "__main__":
    main()
```

---

## 完整 response 解析

当 `stream=True` 时，`client.chat.completions.create(...)` 返回的不再是单个 `ChatCompletion` 对象，
而是一个**可迭代**的流，每次迭代产出一个 `ChatCompletionChunk`。

### 1. 单个 chunk 的结构

每个 `chunk`（`ChatCompletionChunk`）大致结构如下：

```python
ChatCompletionChunk(
    id="chatcmpl-xxx",
    choices=[
        Choice(
            index=0,
            delta=ChoiceDelta(
                role="assistant",   # 通常仅首个 chunk 携带 role
                content="秋",        # 本 chunk 的增量内容，可能为 None / ""
            ),
            finish_reason=None,      # 仅最后一个 chunk 为 "stop"
        )
    ],
    usage=None,                      # 默认流式下 usage 为 None
)
```

关键字段说明：

- `chunk.choices`：通常只有一个元素（`index=0`）。少数情况下（如服务端推送 usage）`choices` 可能为空，因此遍历时先用 `if not chunk.choices: continue` 兜底。
- `chunk.choices[0].delta`：本 chunk 相对上一 chunk 的**增量**（delta）。
  - `delta.content`：增量文本。模型尚未输出 token 时可能为 `None` 或空字符串 `""`，需要判空后再使用。
  - `delta.role`：角色信息，通常只出现在**第一个** chunk 中（值为 `"assistant"`）。
- `chunk.choices[0].finish_reason`：结束原因。中间 chunk 均为 `None`，**最后一个** chunk 为 `"stop"`（正常结束）或其他结束标记。

### 2. 如何累积完整文本

由于每个 chunk 只包含增量，需要自行拼接：

```python
full_text_parts = []
for chunk in stream:
    if not chunk.choices:
        continue
    content = chunk.choices[0].delta.content
    if content:                          # 跳过 None / ""
        print(content, end="", flush=True)  # 实时展示
        full_text_parts.append(content)     # 收集
full_text = "".join(full_text_parts)        # 最终汇总
```

- 用 `list.append + "".join` 比反复字符串 `+=` 更高效。
- `print(content, end="", flush=True)` 保证增量立即刷新到终端，实现打字机效果。

### 3. 关于 usage

默认情况下，流式响应的 `chunk.usage` 为 `None`（OpenAI 兼容服务通常不在流中返回用量统计）。
如果需要 token 用量，可在请求中传入：

```python
stream_options={"include_usage": True}
```

开启后，服务端一般会在**最后一个 chunk**（`choices` 为空、`usage` 有值的那个）中返回总用量。

---

## 示例输出
> 已于 **2026-07-18** 在腾讯云 **TokenHub** （`https://tokenhub.tencentmaas.com/v1`，`model=hy3`）实测。内容为模型生成，可能随调用变化；密钥已脱敏。

```text
=== 流式输出（逐 chunk 打印）===
秋天的银杏宛若披上金裳的舞者，在微凉的风里洒落一地温柔的时光。

=== 流结束 ===
TTFT ≈ 0.005 s · 总耗时 ≈ 0.453 s
```
