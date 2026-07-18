# Cursor × Hy3

在 [Cursor](https://cursor.com) 中通过自定义 OpenAI 兼容接口使用 Hy3（推荐经 OpenRouter；也可直连 TokenHub）。

## 安装与版本

| 项 | 要求 |
|----|------|
| Cursor | 最新稳定版（Settings 中有 Models / OpenAI API Key） |
| 系统 | macOS / Windows / Linux |
| Key | OpenRouter `sk-or-...` 或 TokenHub Key |

## 配置项

### 方式 A：OpenRouter（推荐，多模型统一）

依据 [OpenRouter Cursor 文档](https://openrouter.ai/docs/cookbook/coding-agents/cursor-integration)：

1. `Cursor Settings` → `Models`
2. 填入 **OpenAI API Key** = 你的 OpenRouter Key
3. 开启 **Override OpenAI Base URL**，设为：

```text
https://openrouter.ai/api/v1/cursor
```

> 注意必须是 **`/api/v1/cursor`**，不要只用 `/api/v1`，否则工具调用格式可能异常。

4. 在 Models 列表中 **Add model**，模型 ID：

```text
tencent/hy3
```

5. 在 Chat / Agent 中选中该模型。

| 配置 | 值 |
|------|-----|
| Base URL | `https://openrouter.ai/api/v1/cursor` |
| Model | `tencent/hy3` |
| Auth | OpenRouter API Key |
| 协议 | OpenAI 兼容（Cursor 专用端点） |

### 方式 B：TokenHub 直连

若 Cursor 版本支持自定义 OpenAI Base URL 且接受非 OpenRouter 端点：

| 配置 | 值 |
|------|-----|
| Base URL | `https://tokenhub.tencentmaas.com/v1` |
| Model | `hy3` |
| Auth | TokenHub API Key |

部分 Cursor 功能（Tab 补全、部分 Auto 模式）仍可能走 Cursor 内置模型，以官方说明为准。

## 第一次对话

1. 打开 Chat（`Ctrl/Cmd + L`）。
2. 选择模型 `tencent/hy3`。
3. 发送：`用三句话说明你适合做什么。`
4. 确认能流式返回中文回答。

**截图：** `assets/cursor-first-chat.png`

## 端到端任务 Demo

**任务：** 在当前仓库用 Agent 模式让 Hy3 新增一个纯函数并写单测。

提示词示例：

```text
在 examples/ 下新增 hello_hy3.py，实现 greet(name: str) -> str，
并写 test_hello_hy3.py（unittest）。不要改其它文件。
```

验收：文件生成正确、测试可跑通。  
**截图/GIF：** `assets/cursor-agent-demo.gif`（Agent 改文件过程）。

## 注意事项

- OpenRouter 必须用 `/v1/cursor` 专用 Base URL。
- 模型 ID 用 `tencent/hy3`，与 TokenHub 的 `hy3` 不同。
- Tab 补全通常不受自定义 Key 影响。
- 公司代理 / 系统代理可能导致 TLS 失败；可先在终端 `curl` 通 OpenRouter 再配 Cursor。
- 截图打码 API Key。

## 截图清单

| 文件 | 内容 |
|------|------|
| `assets/cursor-settings.png` | Base URL + Model 配置页 |
| `assets/cursor-first-chat.png` | 第一次对话 |
| `assets/cursor-agent-demo.gif` | Agent 完成小任务 |
