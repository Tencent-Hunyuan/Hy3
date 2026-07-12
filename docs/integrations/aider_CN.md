<p align="left">
  <a href="aider.md">English</a>&nbsp; | &nbsp;中文
</p>

# 在 Aider 中使用 Hy3

## 概述

Aider 可以通过腾讯 TokenHub 的 OpenAI 兼容端点连接 Hy3。本流程已于 2026 年 7 月 12 日使用 Aider `0.86.2` 和模型 ID `hy3` 完成验证。

## 配置

通过环境变量注入凭证，然后从需要读取的仓库目录启动 Aider：

```powershell
$env:OPENAI_API_KEY = "<TENCENT_TOKENHUB_API_KEY>"
aider --model "openai/hy3" `
  --openai-api-base "https://tokenhub.tencentmaas.com/v1" `
  --no-auto-commits
```

不要在终端打印真实 Key，也不要把 Key 录入演示。

![Aider 配置](assets/aider-01-config.png)

## 连接检查

```text
请只回复：Hy3 connection verified
```

![Aider 首次对话](assets/aider-02-first-chat.png)

## 只读仓库任务

使用 `--read` 或 `/read-only` 提供相关文件，然后输入以下原始提示词：

```text
Based only on the read-only files provided, summarize this application's
architecture, identify three concrete risks with file references, and propose
a three-step improvement plan. Do not modify files and do not run Git commands.
```

![Aider 真实只读任务](assets/aider-03-real-task.gif)

## 常见问题

- Aider 提示未知模型时，保留 `openai/` 前缀，并使用模型 ID `hy3`。
- Aider 没有仓库上下文时，从项目根目录启动，并通过 `--read` 或 `/read-only` 添加文件。
- 鉴权失败时，轮换 Key，并确认 Base URL 以 `/v1` 结尾。

## 参考资料

- [腾讯 TokenHub](https://cloud.tencent.com/product/tokenhub)
- [Aider OpenAI 兼容 API](https://aider.chat/docs/llms/openai-compat.html)
