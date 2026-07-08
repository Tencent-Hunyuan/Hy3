# Hy3 API Quickstart

> 5 分钟跑通第一次调用，半小时上手主要能力

## 基础信息

| 项目 | 说明 |
|------|------|
| **Base URL** | `http://127.0.0.1:8000/v1`（本地部署后） |
| **API Key** | 本地部署默认为 `EMPTY`；云端服务请向平台申请 |
| **Model Name** | `hy3`（vLLM/SGLang 启动时通过 `--served-model-name` 指定） |
| **Protocol** | OpenAI API 兼容格式 |
| **Context Length** | 256K tokens |

## 速率限制

本地部署无速率限制。生产使用时建议：

- **RPM**（每分钟请求数）：由部署硬件决定，8×H20 约 50-100 RPM
- **TPM**（每分钟 tokens）：若需限流，可在反向代理层（如 Nginx）配置
- **并发**: 建议使用 `--max-num-seqs`（vLLM）或 `--max-running-requests`（SGLang）控制

## 最小可运行示例

### curl

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer EMPTY" \
  -d '{
    "model": "hy3",
    "messages": [
      {"role": "user", "content": "你好！请简要介绍一下你自己。"}
    ],
    "temperature": 0.9,
    "top_p": 1.0,
    "max_tokens": 512
  }'
```

### Python openai SDK

```bash
pip install openai
```

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="EMPTY",
)

response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "你好！请简要介绍一下你自己。"},
    ],
    temperature=0.9,
    top_p=1.0,
    max_tokens=512,
)
print(response.choices[0].message.content)
```

## 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `temperature` | float | 0.9 | 采样温度，越高越随机。范围 0~2，推荐 0.7~0.9 |
| `top_p` | float | 1.0 | Nucleus 采样概率阈值。推荐 0.9~1.0 |
| `max_tokens` | int | 4096 | 最大输出 token 数。支持到 256K 上下文 |
| `stop` | str/list | null | 停止词，遇到后停止生成 |
| `stream` | bool | false | 是否开启流式输出 |
| `tools` | list | null | 工具定义列表（OpenAI 格式） |
| `tool_choice` | str | "auto" | 工具选择策略："auto" / "required" / "none" |

### 思考模式（Reasoning）

通过 `extra_body` 参数控制，仅 vLLM/SGLang 部署时支持：

```python
extra_body={
    "chat_template_kwargs": {
        "reasoning_effort": "no_think"  # "no_think" | "low" | "high"
    }
}
```

| 取值 | 效果 | 适用场景 |
|------|------|----------|
| `"no_think"` | 直接回答，不展示思考过程（默认） | 闲聊、简单问答、翻译 |
| `"low"` | 快速思考，较短 CoT | 常识推理、简单数学 |
| `"high"` | 深度思考，完整 CoT | 复杂数学、编程、逻辑推理 |

## 常见报错排查

| 错误信息 | 主要原因 | 解决方法 |
|----------|----------|----------|
| `401 Unauthorized` | API Key 不匹配 | 检查 `api_key` 参数 |
| `404 Not Found` | 路由错误或模型未加载 | 确认 `base_url` 末尾有 `/v1` |
| `429 Too Many Requests` | 请求过频 | 退避重试，降低并发 |
| `503 Service Unavailable` | 模型未就绪 / 正在加载 | 等待模型加载完成 |
| `Connection Refused` | 服务未启动 | 确认服务器已启动并监听端口 |
| `context length exceeded` | 输入超 256K | 缩短输入或分段处理 |
| `tool_call parse error` | 工具输出格式异常 | 检查 tool 定义是否符合 schema |

## 部署提示

在运行示例前，需先完成模型部署：

- **vLLM**: 参考 [vLLM recipes](https://recipes.vllm.ai/tencent/Hy3)
- **SGLang**: 参考 [SGLang cookbook](https://lmsysorg.mintlify.app/cookbook/autoregressive/Tencent/Hy3)

---

> 详细示例代码请参见 [`examples/`](./examples/) 目录。
