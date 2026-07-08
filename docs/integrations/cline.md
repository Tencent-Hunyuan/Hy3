# Hy3 with Cline (VS Code)

[Cline](https://github.com/cline/cline) 是 VS Code 上的 AI 编程助手插件，支持 OpenAI 兼容的自定义 API。

## 1. 安装与版本要求

- VS Code ≥ 1.84
- 扩展 `saoudrizwan.claude-dev`（已验证版本 **v4.0.6**）
- 安装命令：

```bash
code --install-extension saoudrizwan.claude-dev
```

- 本地或云端已部署 Hy3 服务

## 2. 配置项

| 配置项 | 值 |
|--------|-----|
| 协议 | OpenAI Compatible |
| API Provider | `OpenAI Compatible` |
| Base URL | `http://127.0.0.1:8000/v1`（本地） |
| API Key | `EMPTY`（本地） |
| Model ID | `hy3` |
| Context Window | `256000`（Hy3 的 256K 上下文） |

### 配置方式一：VS Code UI

1. 点击侧边栏 Cline 图标
2. 顶部 `API Provider` 下拉选 `OpenAI Compatible`
3. 填入上表参数，点 `Done`

### 配置方式二：settings.json（本机已配置）

```json
{
  "cline.apiProvider": "openai",
  "cline.openAiBaseUrl": "http://127.0.0.1:8000/v1",
  "cline.openAiApiKey": "EMPTY",
  "cline.openAiModelId": "hy3"
}
```

## 3. 端到端流程

### 步骤 1：配置

按上文配置方式一/二完成保存。

### 步骤 2：第一次对话

在 Cline Chat 输入：

```
介绍你自己，以及你能帮我做什么。
```

返回 Hy3 回复即连接成功。

### 步骤 3：跑通一个真实任务

```
用 Python Flask 创建一个简单的待办事项 API，包括增删改查，
把文件创建到 ~/projects/todo-app/ 目录。
```

Cline 通过 tool calling 自动建目录、写文件、运行验证。

## 4. 端到端 demo（截图 / GIF）

> 截图位置：见 [screenshots 指南 #3](../../screenshots/README.md#3-cline-vs-code)
> - 图 1：Cline API Provider 配置弹窗
> - 图 2：第一次对话
> - 图 3：真实任务（自动创建 Flask 项目）

## 5. 常见注意事项

- Cline 通过 tool calling 执行文件/终端操作，Hy3 需启用 `--enable-auto-tool-choice`
- 报 `tool_call parse error` 时检查 Hy3 的 `--tool-call-parser hy_v3`
- 支持 `.clinerules` 自定义行为规则
- 上下文窗口建议填 256000 以匹配 Hy3
