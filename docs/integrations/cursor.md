# Hy3 in Cursor

[Cursor](https://cursor.sh/) 是一款 AI-first 代码编辑器，支持接入 OpenAI 兼容的自定义模型。

## 1. 安装与版本要求

- 下载安装 Cursor（Windows / macOS / Linux，版本 ≥ 0.40）
- 本地或云端已部署 Hy3 服务并可访问

## 2. 配置项

| 配置项 | 值 |
|--------|-----|
| 协议 | OpenAI 兼容 |
| OpenAI Key | `EMPTY`（本地）/ 云端服务的 API Key |
| OpenAI Base URL | `http://127.0.0.1:8000/v1`（本地）或你的云端地址 |
| Model 名 | `hy3` |
| 配置入口 | Settings → Models → 关闭内置模型 → 填 OpenAI Key / Base URL → 添加 `hy3` |

## 3. 端到端流程

### 步骤 1：配置

1. 打开 Cursor → `Settings` → `Models`
2. 关闭所有内置模型开关
3. `OpenAI Key` 填 `EMPTY`
4. `OpenAI Base URL` 填 `http://127.0.0.1:8000/v1`
5. 在模型列表添加自定义模型 `hy3`
6. 确认 `Override OpenAI Base URL` 已勾选

### 步骤 2：第一次对话

`Ctrl/Cmd + L` 打开 Chat，输入：

```
你好，介绍一下你能帮我做什么。
```

若返回 Hy3 的回复，说明连接成功。

### 步骤 3：跑通一个真实任务

在 Chat 或 `Ctrl/Cmd + K` 内联编辑中输入：

```
用 Python 写一个命令行工具，递归列出目录下所有文件，
按大小降序排序并输出前 10 个。
```

Hy3 生成代码后点击 `Apply` 写入编辑器，运行验证。

## 4. 端到端 demo（截图 / GIF）

> 截图位置：见 [screenshots 指南 #2](../../screenshots/README.md#2-cursor)
> - 图 1：Cursor Settings → Models 配置页
> - 图 2：Chat 第一次对话
> - 图 3：真实任务（生成并 Apply 代码）

## 5. 常见注意事项

- Hy3 服务需先启动，否则 Cursor 会 fallback 到内置模型
- 本地部署支持 tool calling，Agent 模式可用
- Tab 补全不使用自定义模型，仍需内置模型支持
- 云端部署需填对应 API Key，注意 CORS / 网络可达性
