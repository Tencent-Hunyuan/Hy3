# Hy3 本地部署示例 · 快速上手

> 6 个自包含示例覆盖从“第一次对话”到“思考模式 / 错误处理”的完整路径，全部用 OpenAI 兼容 SDK 调用**本地部署**的 Hy3 服务。

## 1. 环境准备

### 1.1 Python 依赖

```bash
python -m venv .venv
source .venv/bin/activate        
pip install -r requirements.txt
```

### 1.2 启动本地服务（官方推荐）

**vLLM**：

从源码构建 vLLM：

```bash
export VLLM_FLASHINFER_ALLREDUCE_BACKEND=trtllm
vllm serve tencent/Hy3 \
  --tensor-parallel-size 8 \
  --speculative-config.method mtp \
  --speculative-config.num_speculative_tokens 2 \
  --tool-call-parser hy_v3 \
  --reasoning-parser hy_v3 \
  --enable-auto-tool-choice \
  --port 8000 \
  --served-model-name hy3
```

**SGLang**：

```bash
python3 -m sglang.launch_server \
  --model tencent/Hy3 \
  --tp-size 8 \
  --tool-call-parser hunyuan \
  --reasoning-parser hunyuan \
  --speculative-num-steps 2 \
  --speculative-eagle-topk 1 \
  --speculative-num-draft-tokens 3 \
  --speculative-algorithm EAGLE \
  --port 8000 \
  --served-model-name hy3
```

- `--reasoning-parser hy_v3`（vLLM）/ `hunyuan`（SGLang）：开启后 `high` 模式才会返回 `reasoning_content`（见示例 05）。
- `--tool-call-parser` + `--enable-auto-tool-choice`（vLLM）：示例 04 工具调用依赖。

### 1.3 推荐采样参数（官方）

`temperature=0.9`，`top_p=1.0`。

### 1.4 配置 `.env`

```bash
cp .env.example .env
```

默认已填本地部署值（`HY3_BASE_URL=http://127.0.0.1:8000/v1`、`HY3_MODEL=hy3`、`HY3_API_KEY=EMPTY`）。
如需云端 TokenHub，取消注释 `.env.example` 底部的云端段,注意云端用顶层  reasoning_effort ，而非  chat_template_kwargs

## 2. 六个示例的递进关系

| # | 文件 | 主题 | 你学到 |
|---|---|---|---|
| 1 | `01_basic_chat` | 单次 + 多轮对话 | `messages` 结构、模型无记忆、靠重发历史做多轮 |
| 2 | `02_streaming` | 流式输出 | `stream=True`、delta 累积、usage 尾块（`choices` 为空） |
| 3 | `03_latency_compare` | 非流式 vs 流式时延 | TTFT、首字加速比、为什么用流式 |
| 4 | `04_tool_calling` | 函数调用 | tool schema、模型回传 `arguments`、本地执行后回填 |
| 5 | `05_reasoning_mode` | 思考模式 | `reasoning_content`、`no_think`/`low`/`high`、依赖 reasoning parser |
| 6 | `06_error_handling_retry` | 错误处理与重试 | 可重试 / 不可重试错误、退避、401/400 直接失败 |

**递进逻辑** : 基础对话 01 -> 流式输出 02 -> 时延对比 03 -> 工具调用 04 -> 思考模式 05 -> 错误处理与重试 06

## 3. 推荐运行顺序

```bash
python 01_basic_chat.py
python 02_streaming.py
python 03_latency_compare.py
python 04_tool_calling.py
python 05_reasoning_mode.py
python 06_error_handling_retry.py
```

每个示例配套同名 `.md`，讲解原理与真实输出。

## 4. reasoning_effort 控制方式

统一通过 `extra_body` 透传：

```python
extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}}  # 默认，直接回复
extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}}    # 深度思考
```

取值：`no_think`（默认，最快）/ `low` / `high`（数学、代码、复杂推理）。
**必须服务端启用 `--reasoning-parser`，否则该字段不返回**（示例 05 的 `reasoning_content` 因此为空）。

## 5. 常见问题

- **05 的 `high` 模式没有 `reasoning_content`？** 服务端启动未加 `--reasoning-parser hy_v3`（vLLM）/ `hunyuan`（SGLang）。加上即可；否则该字段为空，与示例输出一致。
- **04 工具调用不触发？** 确认 vLLM 加了 `--enable-auto-tool-choice --tool-call-parser hy_v3`。
- **401 / 400？** 见 06：密钥错 = 401、模型名错 = 400，均不可重试，直接报错。
- **连不上 / 超时？** 确认本地服务、`.env` 的 `HY3_BASE_URL` 正确；超时调大 `HY3_TIMEOUT_SECONDS`。
