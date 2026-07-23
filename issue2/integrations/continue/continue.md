# 在 Continue 中使用 Hy3

> English: [continue.en.md](continue.en.md) · [返回索引](../README.md)

Continue 提供 VS Code/JetBrains 扩展和 `cn` CLI。当前配置入口是 `config.yaml`；旧 `config.json` 已弃用。

## 安装与版本

- 在扩展市场安装发布者为 `Continue` 的 **Continue - open-source AI code agent**，或安装官方 `cn` CLI。
- 建议使用当前稳定版。以下 YAML 于 2026-07-23 对照 [OpenAI provider 文档](https://docs.continue.dev/customize/model-providers/top-level/openai)、[config.yaml reference](https://docs.continue.dev/reference)核对。

## 配置

将以下内容保存到 `~/.continue/config.yaml`。推荐把 Key 放入环境 Secret，而不是直接写值：

```yaml
name: Hy3 Agent
version: 1.0.0
schema: v1

models:
  - name: Hy3 via OpenRouter
    provider: openai
    model: tencent/hy3
    apiBase: https://openrouter.ai/api/v1
    apiKey: ${{ secrets.OPENROUTER_API_KEY }}
    capabilities:
      - tool_use
    roles:
      - chat
      - edit
      - apply
    defaultCompletionOptions:
      temperature: 0.9
      maxTokens: 4096
```

自建服务只需把 `apiBase` 改成 `http://127.0.0.1:8000/v1`、`model` 改成 `hy3`，并使用网关要求的 Key。Hy3 属于新模型，显式增加 `tool_use` 可让 Continue 开放 Agent 工具能力。

## 第一次对话

1. 重载 Continue 配置并在模型选择器中选 **Hy3 via OpenRouter**。
2. 切到 Chat 模式，发送：

   ```text
   只根据当前打开的 README 回答：这个仓库是什么？引用你实际读取的文件路径，不要修改文件。
   ```

3. 验收：回答引用正确文件，Continue 日志中的 model 为 `tencent/hy3`，仓库无变化。

## 端到端任务（Agent 模式）

```text
仅修改 issue2/demo/：为 POST /api/research 增加 JSON Content-Type 检查，非 JSON 返回 415；添加覆盖该分支的 HTTP 测试；运行完整 unittest。不要安装依赖，不要提交。
```

显式 `capabilities: [tool_use]` 后才应进入 Agent 模式。接受 Apply 前逐文件查看 diff；结束后在独立终端复跑测试和 `python3 issue2/demo/server.py --check`。

![Evidence Board 离线运行截图](../../assets/evidence-board-offline.png)

## 常见问题

| 症状 | 处理 |
|:---|:---|
| YAML 未生效 | 检查顶层 `name/version/schema`，重载配置并查看 Continue 日志 |
| Agent 模式不可选 | 增加 `capabilities: [tool_use]`，并确认端点确实支持 OpenAI tools |
| 调到 `/responses` 失败 | Hy3 配置使用普通模型名；如版本误判，可加 `useResponsesApi: false` 强制 Chat Completions |
| Secret 解析为空 | 从启动 VS Code 的环境导出 `OPENROUTER_API_KEY`，再完全重启 VS Code |
| Apply 破坏无关文件 | 在 prompt 和 Continue rules 中限制路径，应用前审查 diff |
