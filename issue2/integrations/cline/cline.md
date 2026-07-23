# 在 Cline 中使用 Hy3

> English: [cline.en.md](cline.en.md) · [返回索引](../README.md)

Cline 是 VS Code 编码 Agent，可读写文件、运行命令并使用浏览器。官方仓库确认支持 OpenRouter 与任意 OpenAI-compatible API；本指南使用扩展内的 Provider 表单，避免直接修改其内部 Secret 文件。

## 安装与版本

1. 使用 VS Code 1.93+（Cline 的终端集成功能要求该版本或更高）。
2. 在扩展市场搜索并安装发布者为 `saoudrizwan` 的 **Cline**。
3. 打开扩展详情页记录实际版本；建议使用当前稳定版。本字段于 2026-07-23 对照 [Cline 官方仓库](https://github.com/cline/cline)核对。

## 配置

### OpenRouter（推荐）

在 Cline 设置中选择：

```text
API Provider: OpenRouter
OpenRouter API Key: <通过 Cline Secret 输入框填写>
Model: tencent/hy3
```

### 自建 Hy3

```text
API Provider: OpenAI Compatible
Base URL: http://127.0.0.1:8000/v1
API Key: EMPTY
Model ID: hy3
```

Cline 的 **OpenAI Compatible** 当前走 `/chat/completions`；不要把仅支持 Responses API 的端点误配到此处。Agent 依赖工具调用，自建 vLLM 应包含 `--tool-call-parser hy_v3 --enable-auto-tool-choice`。

## 第一次对话

先关闭自动批准或把它限制为只读操作，然后发送：

```text
只读分析当前工作区：列出顶层目录，读取 README，但不要写文件、运行命令或访问网络。最后说明你实际执行了哪些工具。
```

验收：Cline 的工具时间线只有读取动作；`git status --short` 没有新增修改。

## 端到端任务

复制以下任务到 Cline：

```text
仅修改 issue2/demo/。给问题输入增加前后空白归一化和 10～500 字长度校验；为成功、过短、过长三个分支补 unittest。运行 python3 -m unittest discover -s issue2/demo/tests -v。遇到失败先解释原因，再请求执行修复；不要提交 Git。
```

验收顺序：

1. 审查 Cline 请求的每个写入和命令权限。
2. 确认 diff 没有越过 `issue2/demo/`。
3. 在 VS Code 终端亲自复跑测试，看到退出码 0。
4. 启动 `python3 issue2/demo/server.py` 并打开页面。

![Evidence Board 离线运行截图](../../assets/evidence-board-offline.png)

## 常见问题

| 症状 | 处理 |
|:---|:---|
| 模型列表没有 Hy3 | OpenRouter 列表刷新后搜索 `tencent/hy3`；自建模式手工填写 `hy3` |
| 工具调用退化成文字 | 检查服务的 Hy3 tool-call parser；确认 Provider 是 OpenAI Compatible 而非 native OpenAI |
| 400 参数错误 | 先关闭额外思考参数，用 Hy3 推荐的 `temperature=0.9` 验证基础对话 |
| 自动执行风险过高 | 关闭 Auto Approve，或只允许读文件和安全测试命令 |
| 终端结果未被读取 | 升级 VS Code/Cline，并确认 shell integration 已启用 |

提交前需用真实 Hy3 录制一次 Cline 工具时间线；仓库截图只展示最终可运行作品。
