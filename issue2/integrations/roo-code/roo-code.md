# 在 Roo Code 中使用 Hy3

> English: [roo-code.en.md](roo-code.en.md) · [返回索引](../README.md)

Roo Code 是 VS Code 中支持多模式和配置 Profile 的编码 Agent。官方 Provider 文档列出 **OpenAI Compatible**，适合直接接入 Hy3。

## 安装与版本

1. 在 VS Code 扩展市场安装 **Roo Code**，核对发布者为 `RooVeterinaryInc`（以官方市场页当前信息为准）。
2. 记录扩展详情页中的实际版本，建议使用当前稳定版。
3. 以下字段于 2026-07-23 对照 [Roo Code Provider 文档](https://roocodeinc.github.io/Roo-Code/providers/)核对。

## 配置 Profile

打开 Roo Code → Settings → Provider Profiles，新建 `Hy3`：

```text
API Provider: OpenAI Compatible
Base URL: https://openrouter.ai/api/v1
API Key: <在 Secret 输入框填写>
Model ID: tencent/hy3
Temperature: 0.9
Context Window: 262144
```

自建端点使用：

```text
Base URL: http://127.0.0.1:8000/v1
API Key: EMPTY
Model ID: hy3
```

如果当前版本展示 Native Tools 开关，保持开启；自建端同时启用 Hy3 tool-call parser。上下文值按 OpenRouter 模型页的 262K 展示填写，最终可用长度仍受 Provider 限制。

## 第一次对话

选择 **Ask** 模式，关闭所有写入/命令的自动批准，发送：

```text
读取 README_CN.md，给出三条可以直接从文件核对的 Hy3 信息，每条附文件路径和小节名。不要修改文件或执行命令。
```

验收：Roo 只读取文件，答案可逐条在 README 中找到，工作树未变化。

## 端到端任务

切到 **Code** 模式：

```text
只修改 issue2/demo/。把知识库检索从简单子串匹配重构为可测试的分词计分；中文和英文问题都必须返回稳定排序。先补失败测试，再实现，再运行全部 unittest。不要联网、安装依赖或提交 Git。
```

建议授权策略：允许读 `issue2/demo/`；写入逐次确认；仅批准明确的 `python3 -m unittest ...`。完成后检查工具时间线确实经历“失败测试 → 实现 → 通过测试”，而非只展示最终文本。

![Evidence Board 离线运行截图](../../assets/evidence-board-offline.png)

## 常见问题

| 症状 | 处理 |
|:---|:---|
| Profile 保存后回到其他模型 | 在当前任务顶部重新选择 `Hy3` Profile，新建任务验证 |
| Model ID 不被自动发现 | OpenAI Compatible 允许手工输入；OpenRouter 必须是 `tencent/hy3` |
| 工具调用 JSON 出错 | 开启 Native Tools；检查 vLLM/SGLang 的 Hy3 parser；先减少并行工具数 |
| 上下文溢出 | Context Window 不要超过 Provider 模型页；减少无关文件和终端日志 |
| 自动批准范围过宽 | 用 Profile/模式分别保存最小权限，敏感命令始终手工确认 |

提交前应再录制一次真实 Hy3 的 Roo 工具时间线；本地截图只作为作品运行结果。
