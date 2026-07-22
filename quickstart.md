# Hy3 API Quickstart Guide

## 1. 基础信息 (Basic Info)
- **Base URL**: `https://tokenhub.tencentmaas.com/v1`
- **API Key**: 你的密钥（请替换下文）
- **Model Name**: `hy3-preview` (以腾讯云控制台为准)

## 2. 环境准备
### 确保安装了 OpenAI SDK:
pip install openai


## 3. 最小可运行示例 (Minimal Example)
### Curl

### 替换 YOUR_API_KEY 后运行

curl https://tokenhub.tencentmaas.com/v1/chat/completions\

-H "Content-Type: application/json" \
-H "Authorization: Bearer YOUR_API_KEY" \
-d '{
"model": "hy3-preview",
"messages": [
{
"role": "user",
"content": "你好"
}
]
}'

### Python (OpenAI SDK)
from openai import OpenAI

### 初始化客户端
client = OpenAI(

api_key="YOUR_API_KEY",  # 替换为你申请的 Key

base_url="https://tokenhub.tencentmaas.com/v1"

)

### 发送请求
response = client.chat.completions.create(

model="hy3-preview",

messages=[

{"role": "user", "content": "你好"}

],

temperature=0.7

)

print(response.choices[0].message.content)

## 4. 环境变量配置（推荐生产环境使用）
为避免硬编码API Key，建议使用环境变量注入：

### Windows（PowerShell）
powershell

$env:HY3_API_KEY="YOUR_API_KEY"

$env:HY3_BASE_URL="https://tokenhub.tencentmaas.com/v1"

### Linux/macOS

export HY3_API_KEY="YOUR_API_KEY"

export HY3_BASE_URL="https://tokenhub.tencentmaas.com/v1"

### Python代码示例：

import os

from openai import OpenAI

client = OpenAI(

api_key=os.getenv("HY3_API_KEY"),

base_url=os.getenv("HY3_BASE_URL", "https://tokenhub.tencentmaas.com/v1")

)

## 5. 实战示例导航
本仓库覆盖Hy3 API全场景核心能力，所有示例均经过实战验证：
| 序号 | 目录 | 核心能力 | 解决的实战问题 |
|------|------|----------|----------------|
| 01 | `examples/01_basic_call` | 基础非流式调用 | 验证API连通性，入门首选 |
| 02 | `examples/02_streaming` | 流式传输+首字耗时（TTFT）统计 | 解决流式场景下响应延迟测量问题 |
| 03 | `examples/03_token_stats` | Token消耗统计 | 精确拆分输入/输出Token，便于成本核算 |
| 04 | `examples/04_reasoning_mode` | 思考模式（`reasoning_effort`）控制 | ✅ 解决`high`模式下输出截断问题，区分思考过程与最终回答 |
| 05 | `examples/05_error_retry` | 错误重试机制 | ✅ 实现指数退避重试，覆盖429限流、超时、网络错误场景 |
| 06 | `examples/06_comprehensive_test` | 综合测试套件 | 集成所有功能的一站式测试验证 |

## 6. 核心踩坑指南
### 问题1：开启`reasoning_effort=high`后输出被截断？
**原因**：非流式调用下，深度思考过程会占用大量Token额度。
**解决方案**：必须开启流式传输，监听`chunk.choices[0].delta.reasoning_content`字段。

### 问题2：运行报401「API Key不存在」？
**原因**：TokenHub网关返回的401错误未被OpenAI SDK映射为标准认证异常。
**解决方案**：检查环境变量`HY3_API_KEY`是否正确配置。

### 问题3：流式调用首字耗时（TTFT）过长？
**原因**：`reasoning_effort=high`模式下，TTFT包含模型后台思考耗时。
**解决方案**：属于正常现象，非网络问题。

## 7. 提交前检查清单
- [ ] 所有代码中的明文API Key已替换为环境变量读取
- [ ] `.gitignore`已包含`venv/`/`__pycache__/`/`.env`/`*.log`
- [ ] 深度思考模式下的`max_tokens`已设置为≥4096
- [ ] 所有测试用例在本地验证通过

## 8. FAQ
### Q：如何调整思考强度？
A：通过`extra_body={"reasoning_effort": "none"/"high"}`控制。

### Q：如何查看Token消耗？
A：非流式调用可通过`response.usage`获取，流式调用可在最后一个chunk获取。

### Q：重试次数设置多少合适？
A：建议最大重试次数为3次，配合指数退避策略（等待时间=1s×2^重试次数）。

## 9. 参考文档
- [腾讯云TokenHub官方文档](https://cloud.tencent.com/document/product/1721)
- [腾讯云TokenHub控制台](https://console.cloud.tencent.com/tokenhu