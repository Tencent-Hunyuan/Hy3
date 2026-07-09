# Hy3 API Quickstart Guide

欢迎来到混元 Hy3 快速入门指南。本文档将帮助你在 5 分钟内完成第一次 API 调用，并了解核心参数的使用方法。

## 1. 基础信息 (Basic Info)

- **Base URL**: 请根据你的实际控制台地址确认
- **Model Name**: hy3
- **API Key**: 请在腾讯云控制台获取并妥善保管。
- **Rate Limit**: [例如: 默认限制 60 RPM，如需提升请联系商务]

## 2. 最小可运行示例 (Minimal Example)

### Python SDK (OpenAI Compatible)
推荐使用兼容 OpenAI 格式的 SDK 进行调用。

```python
from openai import OpenAI

client = OpenAI(
    api_key="自己申请的api_key",
    base_url="去打开api调用就可以得到这些代码",
)

response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "你好，请介绍一下你自己"},
    ],
)
print(response.choices[0].message.content)
```

### **cURL 命令**

适合在终端快速测试连通性。

```
curl -X POST 'https://tokenhub.tencentmaas.com/v1/chat/completions' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -d '{
    "model": "hy3",
    "messages": [
      {"role": "user", "content": "你好，请简单介绍一下你自己。"}
    ],
    "stream": false,
    "temperature": 0.9
  }'
```

响应示例：

```
{
  "id": "REPLACED_ID",
  "object": "chat.completion",
  "model": "hy3",
  "created": 1775146513,
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "你好！我是混元，是由腾讯开发的大模型。我的主要功能是基础信息处理与逻辑响应，比如回答各种问题、解决问题、学习新知识、创造内容，还能陪你闲聊呢。如果你有任何问题都可以随时问我哦。"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 22,
    "completion_tokens": 50,
    "total_tokens": 72,
    "prompt_tokens_details": {"cached_tokens": 0},
    "completion_tokens_details": {"reasoning_tokens": 0}
  }
}
```



## 3. 关键参数说明 (Parameters)



| 参数          | 类型  | 说明                                                   |
| :------------ | :---- | :----------------------------------------------------- |
| `temperature` | float | 采样温度 (0-2)。越高越随机，越低越确定。建议 0.7-1.0。 |
| `top_p`       | float | 核采样阈值。建议与 temperature 二选一调整。            |
| `max_tokens`  | int   | 最大生成 token 数。注意不要超过模型的上下文窗口限制。  |
| `stream`      | bool  | 是否开启流式输出。设为 `true` 可获得类似打字机的效果。 |
| `tools`       | list  | 定义工具列表，用于 Function Calling 场景。             |

## **4. 常见报错排查 (Troubleshooting)**

- **401 Unauthorized**: API Key 错误或未生效。请检查 Key 是否正确复制，且账户余额充足。
- **429 Too Many Requests**: 触发限流。请降低请求频率或申请提额。
- **Timeout**: 网络超时。请检查网络连接，或适当增加 `timeout` 参数。