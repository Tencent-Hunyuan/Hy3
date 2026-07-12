<p align="left">
  <a href="README.md">English</a>&nbsp; | &nbsp;中文
</p>

# 在主流 AI 工具中使用 Hy3

本目录提供通过腾讯 TokenHub 接入 Hy3 的已验证方案。所有流程均于 2026 年 7 月 12 日使用当日可获取的最新客户端版本、模型 ID `hy3` 完成首次对话和只读仓库任务验证。

## 集成矩阵

| 工具 | 类型 | 协议 | 状态 | 指南 |
|:---|:---|:---:|:---:|:---|
| Cline | VS Code Agent | Chat Completions | 已验证 | [指南](cline_CN.md) |
| Continue | VS Code / JetBrains 助手 | Chat Completions | 已验证 | [指南](continue_CN.md) |
| Aider `0.86.2` | CLI 编程助手 | Chat Completions | 已验证 | [指南](aider_CN.md) |
| Dify + Tencent TokenHub 插件 `0.0.4` | 低代码 / Agent 平台 | Chat Completions | 已验证 | [指南](dify_CN.md) |
| Codex CLI `0.144.1` | CLI 编程 Agent | Responses API | 已验证 | [指南](codex-cli_CN.md) |

## 公共配置

| 配置项 | 值 |
|:---|:---|
| Base URL | `https://tokenhub.tencentmaas.com/v1` |
| Model ID | `hy3` |
| API Key | 已轮换且有权访问 Hy3 的腾讯 TokenHub Key |

Codex CLI 使用 TokenHub 的 Responses API 兼容层。其他已验证客户端使用 OpenAI 兼容的 Chat Completions 路径，或由供应商插件在内部处理该协议。

## 验证任务

所有真实任务录屏使用同一条只读提示词：

```text
Based only on the read-only files provided, summarize this application's
architecture, identify three concrete risks with file references, and propose
a three-step improvement plan. Do not modify files and do not run Git commands.
```

## 安全

- API Key 仅保存在环境变量、Secret 存储或已遮盖的供应商字段中。
- 不要把 Key 写入源码、提示词、截图、GIF 帧或 Git 历史。
- 验证时使用已轮换的 Key，并在批准前检查每个工具动作。

## 参考资料

- [腾讯 TokenHub](https://cloud.tencent.com/product/tokenhub)
- [腾讯 TokenHub Codex 指南](https://cloud.tencent.com/document/product/1823/133532)
- [Tencent TokenHub Dify 插件](https://marketplace.dify.ai/plugin/lws123321/tencent-tokenhub)
- [Cline OpenAI 兼容供应商](https://docs.cline.bot/provider-config/openai-compatible)
- [Continue OpenAI 供应商](https://docs.continue.dev/customize/model-providers/top-level/openai)
- [Aider OpenAI 兼容 API](https://aider.chat/docs/llms/openai-compat.html)
- [OpenAI Codex 配置参考](https://developers.openai.com/codex/config-reference/)
