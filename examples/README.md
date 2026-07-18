# Hy3 API Examples

本目录提供 6 个可运行示例，说明见仓库根目录 [`quickstart.md`](../quickstart.md)。

## 环境

```bash
pip install openai
```

```powershell
# TokenHub
$env:HY3_API_KEY = "your-key"
$env:HY3_BASE_URL = "https://tokenhub.tencentmaas.com/v1"
$env:HY3_MODEL = "hy3"

# 本地 vLLM / SGLang
# $env:HY3_BASE_URL = "http://127.0.0.1:8000/v1"
# $env:HY3_API_KEY = "EMPTY"
# $env:HY3_MODEL = "hy3"
```

## 列表

| 文件 | 说明 |
|------|------|
| `01_basic_chat` | 单轮 / 多轮对话 |
| `02_streaming` | 流式输出 |
| `03_nonstream_vs_stream` | 非流式与流式时延对比 |
| `04_tool_calling` | 工具调用与多轮回传 |
| `05_reasoning_mode` | 思考模式对比 |
| `06_error_handling_retry` | 错误重试与退避 |

每个示例包含 `.py` 脚本与 `.md` 说明。

## 运行

```bash
cd examples
python 01_basic_chat.py
python 02_streaming.py
python 03_nonstream_vs_stream.py
python 04_tool_calling.py
python 05_reasoning_mode.py
python 06_error_handling_retry.py
```

## 环境变量

| 变量 | 默认值 |
|------|--------|
| `HY3_BASE_URL` | `http://127.0.0.1:8000/v1` |
| `HY3_API_KEY` | `EMPTY` |
| `HY3_MODEL` | `hy3` |
