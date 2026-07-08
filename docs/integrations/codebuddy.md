# Hy3 with CodeBuddy

[CodeBuddy](https://codebuddy.ai/) 是 AI 编程助手（IDE 插件 / 独立客户端），支持自定义 OpenAI 兼容 API。

## 1. 安装与版本要求

- VS Code / JetBrains 插件，或独立客户端（版本 ≥ 1.0）
- 从官网或扩展市场安装「CodeBuddy」
- 本地或云端已部署 Hy3 服务

## 2. 配置项

| 配置项 | 值 |
|--------|-----|
| 协议 | OpenAI Compatible |
| API Base URL | `http://127.0.0.1:8000/v1`（本地） |
| API Key | `EMPTY`（本地部署） |
| Model 名 | `hy3` |
| Max Tokens | 4096 |
| 配置入口 | 设置 → 模型配置 → Provider 选 `Custom OpenAI` |

## 3. 端到端流程

### 步骤 1：配置

1. 打开 CodeBuddy 设置 → 模型配置
2. Provider 选 `Custom OpenAI`
3. 填入 Base URL / API Key / Model `hy3`
4. 保存

### 步骤 2：第一次对话

选中代码后 `Ctrl/Cmd + I` 打开 Chat，输入「介绍一下你自己」验证连通。

### 步骤 3：跑通一个真实任务

```
用 TypeScript 写一个防抖函数 debounce，支持 leading 立即执行选项，
并给出使用示例。
```

CodeBuddy 生成代码并可直接插入编辑器。

## 4. 端到端 demo（截图 / GIF）

> 截图位置：见 [screenshots 指南 #5](../../screenshots/README.md#5-codebuddy)
> - 图 1：CodeBuddy 模型配置页
> - 图 2：第一次对话
> - 图 3：真实任务（生成 TS 防抖函数）

## 5. 常见注意事项

- Agent 模式依赖 tool calling，Hy3 需启用 `--enable-auto-tool-choice`
- SSH 远程开发需保证 Hy3 端口可达
- 自定义模型不支持 CodeBuddy 的部分高级功能（如代码补全）
- 云端部署需配置对应 API Key
