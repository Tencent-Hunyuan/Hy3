# 10 错误处理与重试

对连接错误、超时、限流和服务端错误进行指数退避重试。

## 运行

```bash
uv run --env-file .env python examples/10_error_handling_retry.py
```

## 请求和解析

脚本关闭 SDK 内置自动重试，并将最大尝试次数设置为 3。遇到 `APIConnectionError`、`APITimeoutError`、`RateLimitError` 或 `InternalServerError` 时，等待带随机抖动的指数退避时间后重试；成功后从 `response.choices[0].message.content` 读取文本。

## 输出示例

成功时：

```text
腾讯混元大模型是腾讯自主研发的通用大语言模型，具备多模态理解与生成能力，可处理文本、图像、语音等任务。它支持知识问答、内容创作、逻辑推理、代码编写等场景，并通过持续迭代优化中文理解、长文本处理等能力。作为底层模型，混元已接入腾讯云、微信等生态，为 B 端和 C 端提供 AI 能力支持，注重安全性与合规性。
```

发生可重试错误时，可能看到：

```text
第 1 次请求失败：RateLimitError，1.23s 后重试
```

达到最大重试次数后，脚本会重新抛出最后一次异常。生产环境还应记录 `request_id`，并结合 `Retry-After` 响应头调整等待时间。
