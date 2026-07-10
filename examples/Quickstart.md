# Hy3 API Quickstart

> 面向开发者的 5 分钟快速入门 —— 从零开始调用 Hy3 API。

---

## 目录

- [基本信息](#基本信息)
- [获取 API Key](#获取-api-key)
- [环境准备](#环境准备)
- [最小可运行示例](#最小可运行示例)
  - [cURL](#curl)
  - [Python OpenAI SDK](#python-openai-sdk)
- [核心参数说明](#核心参数说明)
- [思考模式切换](#思考模式切换)
- [速率限制](#速率限制)
- [常见报错排查](#常见报错排查)
- [下一步](#下一步)

---

## 基本信息

|项目|值|
|:-|:-|
|Base URL|`https://tokenhub.tencentmaas.com/v1`|
|API Key|需在 TokenHub 控制台创建|
|Model|`hy3`|
|接口协议|OpenAI API 兼容|
|上下文长度|256K tokens|
|最大输出|128K tokens|
|推荐 temperature|`0.9`|
|推荐 top_p|`1.0`|

---

## 获取 API Key

通过腾讯云 TokenHub 接入：

1. 打开 [TokenHub API Key 管理](https://console.cloud.tencent.com/tokenhub/apikey)
2. 点击 **Create API Key**
3. 设置访问范围（选择 Hy3 或全选）
4. 复制生成的 API Key（格式如 `sk-xxxxxxxx`）

> 免费额度请参考腾讯云 TokenHub 官方文档。

---

## 环境准备

### 安装 OpenAI Python SDK

```bash
pip install openai
```

### 验证 API Key 有效性

```bash
curl -s https://tokenhub.tencentmaas.com/v1/models \
  -H "Authorization: Bearer sk-你的APIKey" | python -m json.tool
```

返回 JSON 列表中包含 `hy3` 即表示可用。

---

## 最小可运行示例

### cURL

```bash
export API_KEY="sk-你的APIKey"

curl -s https://tokenhub.tencentmaas.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "model": "hy3",
    "messages": [
      {"role": "user", "content": "你好！请简单介绍一下你自己。"}
    ],
    "temperature": 0.9,
    "top_p": 1.0,
    "reasoning_effort": "no_think"
  }' | python -m json.tool
```

### Python OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://tokenhub.tencentmaas.com/v1",
    api_key="sk-你的APIKey",  # 替换为你的真实 API Key
)

response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "你好！请简单介绍一下你自己。"},
    ],
    temperature=0.9,
    top_p=1.0,
    extra_body={
        "reasoning_effort": "no_think"
    },
)

print(response.choices[0].message.content)
```

**Example Output：**

```text
你好！我是 Hy3，由腾讯混元团队开发的混合专家（MoE）大语言模型。
我拥有 295B 总参数，激活参数 21B，擅长推理、编程、对话等各类任务。
有什么我可以帮助你的吗？
```

---

## 核心参数说明

|参数|类型|默认值|说明|
|:-|:-|:-|:-|
|`temperature`|float|`1.0`|采样温度 (0~2)。值越低越确定（适合事实问答），值越高越多样（适合创意生成）。推荐 `0.9`|
|`top_p`|float|`1.0`|核采样概率阈值。取值 0~1，推荐 `1.0`。与 temperature 建议只调其一|
|`max_tokens`|int|`4096`|最大生成长度。取值 1~模型上限（Hy3 最大输出 128K）|
|`stop`|str/list|`null`|停止词。遇到这些字符串时停止生成。可传单个字符串或字符串数组|
|`stream`|bool|`false`|是否使用 streaming。`true` 时通过 Server-Sent Events 逐 token 返回|
|`tools`|list|`null`|tool 定义列表。详见[tool calling 示例](04_tool_calling/tool_calling.md)|
|`tool_choice`|str|`"auto"`|tool calling 策略：`"auto"`、`"required"`、`"none"` 或指定 function 名|
|`reasoning_effort`|str|`"no_think"`|reasoning mode（思考模式），通过 `extra_body` 传入|

---

## 思考模式切换

Hy3 支持"快思考"和"慢思考"两种模式，通过 `reasoning_effort` 控制：

|模式|值|适用场景|
|:-|:-|:-|
|**直接回答（快思考）**|`"no_think"`|日常对话、简单问答、翻译、摘要|
|**轻量推理**|`"low"`|中等复杂度任务，如代码补全、结构化输出|
|**深度推理（慢思考）**|`"high"`|复杂数学、逻辑推理、代码生成、多步规划|

```python
# 直接回答模式（快思考）
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "法国的首都是什么？"}],
    extra_body={"reasoning_effort": "no_think"},
)
print(response.choices[0].message.content)
# 输出：法国的首都是巴黎。

# 深度推理模式（慢思考）
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "证明：√2 是无理数。"}],
    extra_body={"reasoning_effort": "high"},
)
print(response.choices[0].message.content)           # 最终回答
# 当 reasoning_effort 为 high/low 时，模型会返回 reasoning_content 字段
reasoning = getattr(response.choices[0].message, 'reasoning_content', None)
if reasoning:
    print("思考过程:", reasoning[:200])
```

> 📖 详细对比见 [Reasoning Mode 示例](05_reasoning_mode/reasoning_mode.md)

---

## 速率限制

|限制项|说明|
|:-|:-|
|速率限制|请参考 TokenHub 官方文档，不同套餐有所不同|
|最大上下文|256K tokens|
|最大输出|128K tokens|
|并发请求|取决于套餐，建议渐进式增加并发测试|

---

## 常见报错排查

|HTTP 状态码|错误类型|常见原因|解决方法|
|:-|:-|:-|:-|
|`401`|Unauthorized|API Key 错误或缺失|检查 `api_key` 是否正确，是否在控制台创建|
|`429`|Rate Limit|请求超过速率限制|降低请求频率，使用指数退避重试|
|`503`|Service Unavailable|服务负载过高或维护中|稍后重试|
|`400`|Bad Request|请求参数格式错误|检查 messages 格式、模型名 (`hy3`) 是否正确|
|`timeout`|—|网络延迟或服务处理过慢|增加 `timeout` 参数（如 `timeout=120`）|

**快速检查：**

```bash
curl -s https://tokenhub.tencentmaas.com/v1/models \
  -H "Authorization: Bearer sk-你的APIKey" \
  -o /dev/null -w "HTTP %{http_code}\n"
```

返回 `200` 即正常。

---

## 下一步

完成快速入门后，推荐按顺序学习以下示例：

|示例|文件|学习内容|
|:-|:-|:-|
|📖 1|[Basic Chat](01_basic_chat/basic_chat.md)|单轮/多轮对话，完整 response 解析|
|📖 2|[Streaming](02_streaming/streaming.md)|流式请求与逐 chunk 解析|
|📖 3|[Streaming vs Non-streaming](03_streaming_comparison/streaming_comparison.md)|首 token 时延与总耗时对比|
|📖 4|[Tool Calling](04_tool_calling/tool_calling.md)|Function calling 与多轮工具循环|
|📖 5|[Reasoning Mode](05_reasoning_mode/reasoning_mode.md)|思考过程开启/关闭对比|
|📖 6|[Error Handling & Retry](06_error_handling/error_handling.md)|超时/限流/重试与退避|
