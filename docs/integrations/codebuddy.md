# Hy3 with CodeBuddy

[CodeBuddy](https://codebuddy.ai/) 是一个 AI 编程助手，支持自定义 OpenAI 兼容 API。

## 配置

1. 打开 CodeBuddy 设置 → 模型配置
2. 选择 **Custom OpenAI** 作为 Provider
3. 填入以下参数：

| 配置项 | 值 |
|--------|-----|
| API Base URL | `http://127.0.0.1:8000/v1` |
| API Key | `EMPTY`（本地部署） |
| Model | `hy3` |
| Max Tokens | 4096 |

## 使用

### Chat 模式

选中代码后按 `Ctrl+I` 打开 CodeBuddy Chat，输入指令：

```
给这个函数添加类型注解和 docstring
```

### 代码生成

```
用 TypeScript 写一个防抖函数，支持立即执行选项
```

### Agent 模式

CodeBuddy 的 Agent 模式利用 tool calling 能力，可以：
- 读取/写入文件
- 执行终端命令
- 搜索项目代码
- 创建和修改文件

## 验证

确认连接成功：CodeBuddy 状态栏会显示已连接的模型名。

## 注意事项

- CodeBuddy 的 Agent 模式需要 tool calling 支持，Hy3 需启用 `--enable-auto-tool-choice`
- 如果使用 SSH 远程开发，确保 Hy3 端口可访问
- 自定义模型不支持 CodeBuddy 的某些高级功能（如代码补全）

## 截图

详见 [截图指南](../../screenshots/README.md#5-codebuddy)。 注意：CodeBuddy 需要从官网下载安装，当前环境未安装。
