<p align="left">
  <a href="dify.md">English</a>&nbsp; | &nbsp;中文
</p>

# 在 Dify 中使用 Hy3

## 概述

社区版 **Tencent TokenHub** 模型供应商插件可以让 Dify 直接连接 TokenHub，并将 Hy3 注册为对话模型。本流程已于 2026 年 7 月 12 日使用当日最新 Dify 版本和 `lws123321/tencent-tokenhub` 插件 `0.0.4` 完成验证。

## 配置

1. 打开 **Plugins**，安装 `lws123321` 发布的 **Tencent TokenHub**。
2. 打开 **Settings → Model Provider → Tencent TokenHub**。
3. 填写 TokenHub API Key。保留默认 API Base URL，或填写 `https://tokenhub.tencentmaas.com/v1`。
4. 在工作流 LLM 节点中选择模型 `hy3`。

![Dify 腾讯 TokenHub 配置](assets/dify-01-config.png)

## 连接检查

创建 **用户输入 → LLM → 直接回复** 工作流，然后发送：

```text
请只回复：Hy3 connection verified
```

![Dify 首次对话](assets/dify-02-first-chat.png)

## 只读文档任务

增加文件输入，将解析后的文本传给 Hy3 LLM 节点，并使用以下原始提示词：

```text
Based only on the read-only files provided, summarize this application's
architecture, identify three concrete risks with file references, and propose
a three-step improvement plan. Do not modify files and do not run Git commands.
```

![Dify 真实只读任务](assets/dify-03-real-task.gif)

## 常见问题

- 请使用 **Tencent TokenHub** 供应商，不要继续采用本指南旧版本中的通用 OpenAI-compatible 供应商。
- 确认 Key 有权访问 Hy3，且所选模型为 `hy3`。
- 自定义 API Base URL 时必须使用 HTTPS，并以 `/v1` 结尾。

## 参考资料

- [Tencent TokenHub Dify 插件](https://marketplace.dify.ai/plugin/lws123321/tencent-tokenhub)
- [腾讯 TokenHub](https://cloud.tencent.com/product/tokenhub)
