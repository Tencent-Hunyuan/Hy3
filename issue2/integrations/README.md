# 在主流 AI 工具中使用 Hy3

> English: [README.en.md](README.en.md)

这组指南统一使用 Hy3 的 OpenAI 兼容接口，覆盖网页/API、终端和 VS Code Agent。每篇都包含安装要求、完整配置、第一次对话、一个端到端真实任务和排错说明。

| 工具 | 形态 | 指南 | 真实任务 |
|:---|:---|:---|:---|
| OpenRouter | 聚合网页/API | [打开](openrouter/openrouter.md) | 用工具调用检索资料并生成证据报告 |
| Aider | 终端编码 Agent | [打开](aider/aider.md) | 创建并测试一个 Python slug 工具 |
| Cline | VS Code Agent | [打开](cline/cline.md) | 修复待办应用并运行测试 |
| Continue | VS Code/CLI Agent | [打开](continue/continue.md) | 用 Agent 模式补输入校验和测试 |
| Roo Code | VS Code Agent | [打开](roo-code/roo-code.md) | 跨文件重构并验证回归测试 |

## 两种端点

| 配置 | OpenRouter | 自建 vLLM/SGLang |
|:---|:---|:---|
| Base URL | `https://openrouter.ai/api/v1` | `http://127.0.0.1:8000/v1` |
| Model | `tencent/hy3` | `hy3`（以部署时的 served name 为准） |
| API Key | `OPENROUTER_API_KEY` | 常用 `EMPTY`，以网关要求为准 |
| 协议 | OpenAI Chat Completions | OpenAI Chat Completions |

## 统一验收任务

为了让不同工具的结果可比较，指南都要求工具在 `issue2/demo/` 上完成一个可运行改动，并执行：

```bash
cd issue2/demo
python3 -m unittest discover -s tests -v
python3 server.py --check
```

最终页面截图见 [Evidence Board 离线模式](../assets/evidence-board-offline.png)。该截图只证明本地作品与离线路径可运行；使用真实 Hy3 的工具交互录屏需要配置自己的端点后另行采集。

## 安全约定

- 不把 Key 写进 Markdown、截图、仓库文件或浏览器 `localStorage`。
- 优先使用环境变量或工具自带的 Secret 管理。
- 自建服务必须在启动时开启 Hy3 对应的 tool-call parser，Agent 模式才可可靠使用工具。
- 先以只读或需确认模式运行编码 Agent，再按任务逐项授权命令和文件修改。
