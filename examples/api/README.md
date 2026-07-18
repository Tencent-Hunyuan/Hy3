# Hy3 API Examples

可运行示例集合，配合根目录 [quickstart.md](../../quickstart.md) 使用。

## 环境准备

```bash
cd examples/api
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，填入 HY3_API_KEY
```

必需环境变量：

| 变量 | 说明 | 默认 |
|---|---|---|
| `HY3_API_KEY` | TokenHub API Key | （必填） |
| `HY3_BASE_URL` | API 地址 | `https://tokenhub.tencentmaas.com/v1` |
| `HY3_MODEL` | 模型名 | `hy3` |
| `HY3_MOCK` | `1` 时离线 mock，不发真实请求 | 关闭 |

## 示例列表

| # | 目录 | 能力 |
|---|---|---|
| 01 | [01_basic_chat](./01_basic_chat/) | 单轮 / 多轮对话 |
| 02 | [02_streaming](./02_streaming/) | 流式请求 + chunk 解析 |
| 03 | [03_latency_compare](./03_latency_compare/) | 非流式 vs 流式时延 |
| 04 | [04_tool_calling](./04_tool_calling/) | 工具调用 + 多轮循环 |
| 05 | [05_reasoning_mode](./05_reasoning_mode/) | 思考模式开 / 关 |
| 06 | [06_error_handling](./06_error_handling/) | 超时 / 限流 / 重试退避 |

每个目录含 `README.md`（请求说明、响应解析、示例输出）与 `main.py`。

```bash
python 01_basic_chat/main.py
python 02_streaming/main.py
# ...
```

无 Key 时可先：

```bash
HY3_MOCK=1 python 01_basic_chat/main.py
```

## 安全提示

- 不要把真实 Key 写进代码或提交 `.env`
- 分享日志前脱敏 `Authorization`、request / response id
- 示例 README 中的输出为 **2026-07-18** 在 TokenHub（`model=hy3`）实测后脱敏写入；文案与时延每次运行可能变化
