# Hy3 with Cline (VS Code)

[Cline](https://github.com/cline/cline) 是 VS Code 上的 AI 编程助手插件，支持自定义 API 提供商。

## 安装

1. 在 VS Code 扩展市场搜索 "Cline" 并安装
2. 安装后点击侧边栏 Cline 图标打开面板

## 配置

1. 点击 Cline 面板顶部的 **API Provider** 下拉菜单
2. 选择 **OpenAI Compatible**
3. 填入以下参数：

| 配置项 | 值 |
|--------|-----|
| API Provider | `OpenAI Compatible` |
| Base URL | `http://127.0.0.1:8000/v1` |
| API Key | `EMPTY`（本地） |
| Model ID | `hy3` |
| Context Window | `256000`（Hy3 的 256K 上下文） |

4. 点击 **Done** 保存

## 验证

在 Cline Chat 中输入：

```
介绍你自己，以及你能帮我做什么。
```

如果 Hy3 服务正常运行，Cline 会显示模型的回复。

## 能力支持

| 功能 | 支持情况 |
|------|----------|
| Chat | ✅ |
| Code 生成/编辑 | ✅ |
| Tool Calling | ✅（需要 Hy3 启用 `--enable-auto-tool-choice`） |
| MCP Server | ✅ |
| 文件读写 | ✅（通过 tool calling） |
| 终端命令 | ✅（通过 tool calling） |
| Streaming | ✅ |

## 示例任务

### 创建一个 Python Web 服务器

```
用 Python Flask 创建一个简单的待办事项 API，包括增删改查。
创建文件到 ~/projects/todo-app/ 目录。
```

Cline 会通过 tool calling 自动创建文件和目录。

## 注意事项

- Cline 通过 tool calling 执行文件操作，确保 Hy3 部署时启用了 `--enable-auto-tool-choice`
- 如果遇到 `tool_call parse error`，检查 Hy3 服务的 tool-call-parser 参数
- Cline 支持 `.clinerules` 文件自定义行为规则

## 截图

> 待补充：Cline 配置页面截图 + 对话截图
