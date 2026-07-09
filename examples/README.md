# Hy3 API Examples

这个目录提供一组面向开发者的 Hy3 API 示例，用来配合仓库根目录的
`quickstart.md` 使用。目标是先用最小示例跑通第一次调用，再在半小时内了解
常用能力：基础对话、流式输出、工具调用、思考模式、错误处理与重试。

## 准备环境

安装依赖：

```bash
pip install -r examples/requirements.txt
```

配置 API 信息。Windows PowerShell：

```powershell
$env:HY3_BASE_URL = "http://127.0.0.1:8000/v1"
$env:HY3_API_KEY = "EMPTY"
$env:HY3_MODEL = "hy3"
```

macOS / Linux：

```bash
export HY3_BASE_URL="http://127.0.0.1:8000/v1"
export HY3_API_KEY="EMPTY"
export HY3_MODEL="hy3"
```

如果你的服务地址、模型名或密钥来源不同，请按实际接入信息替换。不要把真实
API key 提交到代码仓库。

## 示例列表

| 编号 | 文档 | 脚本 | 覆盖能力 |
| --- | --- | --- | --- |
| 01 | [01_basic_chat.md](01_basic_chat.md) | [01_basic_chat.py](01_basic_chat.py) | 单轮对话、多轮上下文 |
| 02 | [02_streaming.md](02_streaming.md) | [02_streaming.py](02_streaming.py) | 流式请求、逐 chunk 解析 |
| 03 | [03_streaming_vs_non_streaming.md](03_streaming_vs_non_streaming.md) | [03_streaming_vs_non_streaming.py](03_streaming_vs_non_streaming.py) | 非流式与流式的首 token 时延、总耗时对比 |
| 04 | [04_tool_calling.md](04_tool_calling.md) | [04_tool_calling.py](04_tool_calling.py) | 一次工具调用、工具结果回填、多轮工具循环基础结构 |
| 05 | [05_reasoning_mode.md](05_reasoning_mode.md) | [05_reasoning_mode.py](05_reasoning_mode.py) | `reasoning_effort` 思考模式开关对比 |
| 06 | [06_error_handling_retry.md](06_error_handling_retry.md) | [06_error_handling_retry.py](06_error_handling_retry.py) | 超时、限流、网络错误的重试与退避 |

建议按编号顺序阅读。每个示例文档都应包含三部分：

- 完整请求：展示 `client.chat.completions.create(...)` 的关键参数。
- 完整 response 解析：说明从返回对象中读取哪些字段。
- 示例输出：给出一次可能的运行结果，便于对照本地输出是否正常。

## 运行示例

单独运行任意脚本：

```bash
python examples/01_basic_chat.py
python examples/02_streaming.py
python examples/03_streaming_vs_non_streaming.py
python examples/04_tool_calling.py
python examples/05_reasoning_mode.py
python examples/06_error_handling_retry.py
```

如果你在 `examples` 目录内运行，可以去掉路径前缀：

```bash
python 06_error_handling_retry.py
```

## 常见 response 解析方式

非流式对话返回完整结果，通常读取：

```python
content = response.choices[0].message.content
print(content)
```

流式对话返回多个增量 chunk，通常逐个读取：

```python
for chunk in stream:
    if not chunk.choices:
        continue
    delta = chunk.choices[0].delta
    if delta and delta.content:
        print(delta.content, end="", flush=True)
```

工具调用示例会先读取模型返回的 `message.tool_calls`，本地执行对应函数后，再把
工具结果用 `role="tool"` 追加回 `messages`，最后发起第二次模型调用生成面向用户
的回答。

## 常见问题

| 现象 | 可能原因 | 处理方式 |
| --- | --- | --- |
| `401` 或认证失败 | API key 无效、未设置或过期 | 检查 `HY3_API_KEY`，确认使用了正确密钥 |
| `404` 或模型不存在 | `HY3_MODEL` 与服务端模型名不一致 | 替换为当前可用的 Hy3 模型名 |
| `429` 或 `RateLimitError` | 请求过于频繁或触发速率限制 | 降低并发，使用退避重试，参考 06 示例 |
| `APITimeoutError` | 请求生成时间超过客户端超时设置 | 增大 `timeout`，减少 `max_tokens`，或启用重试 |
| `APIConnectionError` | 网络连接、代理或服务地址异常 | 检查网络、代理、`HY3_BASE_URL` 配置 |
| 流式输出为空 | 没有正确读取 `delta.content` | 对照 02 示例逐 chunk 解析 |

更多基础接入信息，例如 base url、model 名、参数说明、curl 最小示例和 Python
OpenAI SDK 最小示例，应放在仓库根目录的 `quickstart.md` 中。
