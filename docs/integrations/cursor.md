# Hy3 in Cursor

[Cursor](https://cursor.sh/) 是一款 AI-first 的代码编辑器，支持自定义 OpenAI 兼容的 API 提供商。

## 配置步骤

1. 打开 Cursor → Settings → Models
2. 关闭所有内置模型开关
3. 在 **OpenAI Key** 填入你的 API Key
4. 在 **OpenAI Base URL** 填入 Hy3 服务的地址
5. 添加自定义模型名 `hy3`
6. 在 **Override OpenAI Base URL** 中再次确认地址

### 参数

| 项 | 值 |
|---|-----|
| OpenAI Key | `EMPTY`（本地）或你的 API Key |
| OpenAI Base URL | `http://127.0.0.1:8000/v1` |
| Model | `hy3` |

## 使用

配置完成后：

1. `Ctrl+K` / `Cmd+K` 打开内联编辑
2. `Ctrl+L` / `Cmd+L` 打开 Chat 面板
3. Agent / Ask / Edit 三种模式均可使用

### 示例任务

在 Cursor Chat 中输入：

```
用 Python 写一个命令行工具，可以递归列出目录下所有文件的大小并排序
```

Hy3 会自动生成代码并可以 Apply 到编辑器中。

## 注意事项

- 确保 Hy3 服务先启动，Cursor 启动时如果连不上会 fallback 到其他模型
- 本地部署下支持 tool calling，Agent 模式可用
- Cursor 的 Tab 补全功能不使用自定义模型，仍需内置模型
- 如果使用云端 Hy3 部署，需要配置对应的 API Key

## 截图

详见 [截图指南](../../screenshots/README.md#2-cursor)。
