<p align="left">
   <a href="quickstart.md">English</a>&nbsp;｜&nbsp;中文
</p>
<br>
# Hy3 API 快速入门指南

> **目标**: 在 **5 分钟**内完成首次成功的 API 调用，**30 分钟**内掌握核心功能。

---

## 1. 前提条件

| 要求 | 详情 |
|---|---|
| Python | >= 3.9 |
| openai SDK | `pip install openai>=1.30.0` |
| 硬件（自托管） | 8 张高显存 GPU（H20-3e 或更好） |
| 服务引擎 | [vLLM](https://github.com/vllm-project/vllm) 或 [SGLang](https://github.com/sgl-project/sglang) |

---

## 2. API 基础

### 端点

```
POST http://<host>:<port>/v1/chat/completions
```

### 模型标识

| 模型 | 说明 |
|---|---|
| `hy3` | Hy3 完整模型（295B MoE，21B 激活参数） |
| `Hy3-FP8` | FP8 量化版本（更低显存需求） |

### 认证

**自托管**部署使用任意非空字符串作为 API 密钥：

```
Authorization: Bearer EMPTY
```

**云托管**服务（如腾讯云混元、OpenRouter）使用平台提供的 API 密钥。

### 速率限制

自托管部署没有内置速率限制，吞吐量取决于 GPU 资源。云服务商可能设有每分钟或每日配额——请咨询您的服务商文档。

---

## 3. 首次 API 调用（5 分钟）

### 方式 A：curl

```bash
curl -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer EMPTY" \
  -d '{
    "model": "hy3",
    "messages": [
      {"role": "user", "content": "什么是 Hy3？"}
    ],
    "temperature": 0.9,
    "top_p": 1.0,
    "max_tokens": 512
  }'
```

**预期响应：**

```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1720000000,
  "model": "hy3",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hy3 是腾讯开发的 2950 亿参数混合专家（MoE）模型...",
        "reasoning_content": null
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 12,
    "completion_tokens": 156,
    "total_tokens": 168
  }
}
```

### 方式 B：Python（OpenAI SDK）

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="EMPTY",  # 自托管使用任意非空字符串
)

response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "什么是 Hy3？"}
    ],
    temperature=0.9,
    top_p=1.0,
    max_tokens=512,
)

print(response.choices[0].message.content)
```

---

## 4. 核心参数

### 生成控制

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `temperature` | float | 0.9 | 采样温度。越高越有创意。范围：0.0 - 2.0 |
| `top_p` | float | 1.0 | 核采样。越低越集中。范围：0.0 - 1.0 |
| `max_tokens` | int | None | 最大生成 token 数。模型上下文：256K tokens |
| `stop` | str / list | None | 停止序列。最多支持 4 个序列 |

> **推荐**：通用场景使用 `temperature=0.9`，`top_p=1.0`。需要确定性输出时设置 `temperature=0.0`。

### 推理模式（深度思考）

Hy3 支持可配置的推理深度。启用后，响应会包含 `reasoning_content` 字段，展示模型的思考过程。

**云端 API**（如腾讯 TokenHub、OpenRouter）：

```python
extra_body={"reasoning_effort": "high"}  # "no_think" | "low" | "high"
```

**自托管**（vLLM / SGLang）：

```python
extra_body={
    "chat_template_kwargs": {
        "reasoning_effort": "high"  # "no_think" | "low" | "high"
    }
}
```

| 等级 | 适用场景 |
|---|---|
| `"no_think"` | 直接回答、简单问答（默认） |
| `"low"` | 轻度推理、基础逻辑任务 |
| `"high"` | 深度思维链，适用于复杂数学、编程、分析 |

启用推理后，响应会包含 `reasoning_content` 字段，展示模型的思考过程。

### 工具调用（Function Calling）

需要服务端配置：

**vLLM：**
```bash
python -m vllm.entrypoints.openai.api_server \
  --model tencent/Hy3 \
  --tool-call-parser hy_v3 \
  --enable-auto-tool-choice
```

**SGLang：**
```bash
python -m sglang.launch_server \
  --model tencent/Hy3 \
  --tool-call-parser hunyuan
```

---

## 5. 流式响应

启用实时 token 流式传输以降低延迟：

```python
stream = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "解释量子计算"}],
    temperature=0.9,
    stream=True,
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
```

---

## 6. 示例索引

| # | 主题 | 文件 | 说明 |
|---|---|---|---|
| 01 | 基础对话 | [01_basic_chat.py](./examples/01_basic_chat.py) | 单轮和多轮对话 |
| 02 | 流式请求 | [02_streaming.py](./examples/02_streaming.py) | 流式请求与 chunk 处理 |
| 03 | 延迟对比 | [03_latency_compare.py](./examples/03_latency_compare.py) | 流式 vs 非流式性能 |
| 04 | 工具调用 | [04_tool_calling.py](./examples/04_tool_calling.py) | 函数调用与多轮循环 |
| 05 | 推理模式 | [05_reasoning_mode.py](./examples/05_reasoning_mode.py) | 推理开关对比 |
| 06 | 错误处理 | [06_error_handling.py](./examples/06_error_handling.py) | 重试、退避与容错模式 |

---

## 7. 故障排查

### CUDA 显存溢出（OOM）

**症状：** 服务崩溃并报 `CUDA out of memory` 错误。

**解决方案：**
1. 使用 `Hy3-FP8` 替代完整模型以降低显存占用。
2. 在 vLLM/SGLang 启动参数中减小 `--max-model-len`。
3. 启用张量并行：`--tensor-parallel-size 8`。

### 客户端超时

**症状：** 请求在收到响应前超时。

**解决方案：**
1. 增加客户端超时时间：`client = OpenAI(timeout=300)`。
2. 使用流式模式逐步接收 token。
3. 减小请求中的 `max_tokens`。

### 空响应或乱码

**症状：** 响应内容为空或无意义。

**解决方案：**
1. 确认模型已完全加载后再发送请求。
2. 检查 `temperature` 是否在 [0.0, 2.0] 范围内。
3. 确保服务端的 `--tool-call-parser` 与工具调用格式匹配。

### 连接被拒绝

**症状：** `ConnectionError: [Errno 111] Connection refused`

**解决方案：**
1. 验证服务是否运行：`curl http://127.0.0.1:8000/health`。
2. 检查配置端口的防火墙规则。
3. 如果从其他机器访问，确保设置了 `--host 0.0.0.0`。

---

## 8. 环境变量配置

所有示例均支持环境变量配置，以适应灵活的部署需求：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `HY3_BASE_URL` | `http://127.0.0.1:8000/v1` | API 端点 |
| `HY3_API_KEY` | `EMPTY` | API 密钥 |
| `HY3_MODEL` | `hy3` | 模型标识 |

复制 [`.env.example`](../.env.example) 到 `.env` 并填入你的配置：

```bash
cp .env.example .env
# 编辑 .env 填入你的配置
```

---

## 9. 更多资源

- [Hy3 GitHub 仓库](https://github.com/Tencent-Hunyuan/Hy3)
- [vLLM 文档](https://docs.vllm.ai/)
- [SGLang 文档](https://sgl-project.github.io/)
- [OpenAI Python SDK 参考](https://platform.openai.com/docs/api-reference)
