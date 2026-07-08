# Hy3 with Roo Code (VS Code)

[Roo Code](https://github.com/RooVetGit/Roo-Code) 是 VS Code 上的自主 AI 编程 Agent 插件（Cline 分支），支持 OpenAI 兼容自定义模型。

## 1. 安装与版本要求

- VS Code ≥ 1.84
- 扩展 `rooveterinaryinc.roo-cline`（已验证版本 **v3.54.0**）

```bash
code --install-extension rooveterinaryinc.roo-cline
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
| 配置入口 | 侧边栏 Roo Code → 顶部 Profile/API 设置 |

## 3. 端到端流程

### 步骤 1：配置

1. 点击侧边栏 Roo Code 图标
2. 顶部 API Provider 选 `OpenAI Compatible`
3. 填 Base URL / API Key / Model ID `hy3`
4. 保存

### 步骤 2：第一次对话

在 Roo Code Chat 输入「介绍一下你自己」，返回 Hy3 回复即连接成功。

### 步骤 3：跑通一个真实任务

```
在当前工作区创建一个 scripts/backup.sh，
把指定目录打包成带日期的 tar.gz，并加一句 echo 日志。
```

Roo Code 通过 tool calling 创建文件并执行。

## 4. 端到端 demo（截图 / GIF）

> 截图位置：见 [screenshots 指南](../../screenshots/README.md)
> - 图 1：Roo Code API Provider 配置
> - 图 2：第一次对话
> - 图 3：真实任务（自动创建脚本）

## 5. 常见注意事项

- Roo Code 通过 tool calling 操作文件/终端，Hy3 需启用 `--enable-auto-tool-choice`
- 支持多种「模式」（Code / Architect / Ask），按需切换
- 自定义 Mode 可在 `.roomodes` 中定义
- 上下文窗口建议填 256000 匹配 Hy3
