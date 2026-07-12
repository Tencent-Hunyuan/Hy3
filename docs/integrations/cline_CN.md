<p align="left">
  <a href="cline.md">English</a>&nbsp; | &nbsp;中文
</p>

# 在 Cline 中使用 Hy3

## 概述

Cline 的 **OpenAI Compatible** 供应商支持 TokenHub Base URL、API Key 和 Hy3 模型 ID。本流程已使用 2026 年 7 月 12 日可获取的最新 Cline 版本完成验证。

## 配置

打开 **Cline → Settings → API Configuration**，填写：

| 配置项 | 值 |
|:---|:---|
| API Provider | `OpenAI Compatible` |
| Base URL | `https://tokenhub.tencentmaas.com/v1` |
| API Key | 腾讯 TokenHub Key |
| Model ID | `hy3` |

![Cline 配置](assets/cline-01-config.png)

## 连接检查

```text
请只回复：Hy3 connection verified
```

![Cline 首次对话](assets/cline-02-first-chat.png)

## 只读仓库任务

只附加允许 Cline 读取的文件，保持写入和命令审批关闭，并输入以下原始提示词：

```text
Based only on the read-only files provided, summarize this application's
architecture, identify three concrete risks with file references, and propose
a three-step improvement plan. Do not modify files and do not run Git commands.
```

![Cline 真实只读任务](assets/cline-03-real-task.gif)

## 常见问题

- 确认 Base URL 包含 `/v1`，模型 ID 准确填写为 `hy3`。
- 工具调用失败时，先重试纯对话模式，并逐项检查请求的动作。
- Key 如果出现在源码、终端历史或截图中，必须立即轮换。

## 参考资料

- [腾讯 TokenHub](https://cloud.tencent.com/product/tokenhub)
- [Cline OpenAI Compatible 供应商](https://docs.cline.bot/provider-config/openai-compatible)
