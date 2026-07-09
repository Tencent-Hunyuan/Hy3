# Hy3 主流 AI 产品接入指南

本目录面向终端用户，说明如何在常见 AI 产品、IDE、CLI 工具、VS Code 插件和自托管平台中使用 Hy3，并给出一个基于 Hy3 的小作品 demo 方案。

## 通用配置

Hy3 提供 OpenAI Compatible 接口，只要工具支持自定义 OpenAI 兼容服务，一般都可以按以下方式配置。

| 配置项 | 本地 vLLM/SGLang | OpenRouter | 腾讯云 TokenHub |
| --- | --- | --- | --- |
| Base URL | `http://127.0.0.1:8000/v1` | `https://openrouter.ai/api/v1` | `https://tokenhub.tencentmaas.com/v1` |
| Model | `hy3` | `tencent/hy3-295b-a21b` | `hy3-preview` |
| Protocol | OpenAI Compatible | OpenAI Compatible | OpenAI Compatible |
| API Key | `EMPTY` 或任意 | OpenRouter Key | TokenHub Key |

> 建议把 API Key 配置为本地环境变量，避免写进截图、配置文件或公开仓库。
>
> ```bash
> export HY3_API_KEY="your-api-key"
> export HY3_BASE_URL="https://openrouter.ai/api/v1"
> ```
>
> Windows PowerShell:
> ```powershell
> $env:HY3_API_KEY="your-api-key"
> $env:HY3_BASE_URL="https://openrouter.ai/api/v1"
> ```

## 工具指南

### 本 PR 新增（聚焦 CLI / 自托管工具）

| 工具 | 类型 | 指南 |
| --- | --- | --- |
| Codex CLI | AI 工具（OpenAI 官方 CLI） | [codex-cli.md](./codex-cli.md) |
| Aider | AI 结对编程 CLI | [aider.md](./aider.md) |
| Claude Code | Anthropic 官方 AI CLI | [claude-code.md](./claude-code.md) |
| Continue | VS Code 插件 | [continue.md](./continue.md) |
| Open WebUI | 自托管大模型 Web 界面 | [open-webui.md](./open-webui.md) |

### 相关参考

社区中还有其他同学贡献了不同工具的接入方案，可互为补充：

- OpenRouter / Cursor / CodeBuddy / WorkBuddy / Cline / Roo Code / Dify：参见 PR #19
- CLine / CodeBuddy IDE / OpenRouter / Roo Code / ClaudeCode：参见 PR #33

## 小作品 Demo

示例小作品是一个基于 Hy3 的科普动画生成网站 **Vibemotion**：输入任意科普主题，Hy3 生成一段生动的解说词和一段可在浏览器中运行的 p5.js 动画。

- 独立仓库：[xy200303/hy3-vibemotion](https://github.com/xy200303/hy3-vibemotion)
- 核心能力：推理 + 长文生成
- 开发工具：Aider + Hy3（呼应本目录中的 Aider 接入指南）
- 运行方式：见仓库 README

## 使用建议

1. **先通后精**：第一次接入时先做一个最小对话请求，确认 API Key、Base URL 和模型名无误。
2. **协议选择**：如果工具中有 “OpenAI Compatible”、“Custom OpenAI”、“OpenAI API Compatible” 等选项，优先选择这些模式。
3. **Base URL 不要重复 `/v1`**：如果工具默认自动追加 `/v1`，不要重复填写成 `/v1/v1`。
4. **模型名与服务商对齐**：本地部署一般用 `hy3`；OpenRouter 用 `tencent/hy3-295b-a21b`；TokenHub 用 `hy3-preview`。
5. **开启流式输出**：大部分工具默认开启 `stream`，如果手动关闭，长回复可能超时。
6. **Reasoning 模式**：复杂任务（代码、数学、推理）可在 `extra_body` 或工具高级设置里设置 `reasoning_effort` 为 `high`；普通对话用 `no_think`。
7. ** troubleshooting**：
   - `401`：检查 API Key 是否正确，以及是否多写了 `Bearer ` 前缀（多数工具会自动加）。
   - `404`：检查 Base URL 是否多写或少写 `/v1`。
   - `429`：触发限流或配额限制，降低并发或稍后重试。
