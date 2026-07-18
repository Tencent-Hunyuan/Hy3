# WorkBuddy × Hy3

[WorkBuddy](https://cloud.tencent.com/document/product/1823/131902) 是腾讯云全场景桌面 AI 智能体，可配置 TokenHub / OpenRouter 上的 Hy3。  
**以下路径均相对于仓库根目录 `Hy3/`。**

官方说明：[TokenHub × WorkBuddy](https://cloud.tencent.com/document/product/1823/131902)

## 本目录文件

| 文件 | 用途 |
|------|------|
| [`docs/integrations/workbuddy/settings.tokenhub.json`](./settings.tokenhub.json) | TokenHub 自定义模型表单对照 |
| [`docs/integrations/workbuddy/settings.openrouter.json`](./settings.openrouter.json) | OpenRouter 对照 |

```bash
bash docs/integrations/sync_env.sh
# 生成 docs/integrations/workbuddy/.env；在 WorkBuddy UI 按 JSON 字段填写
```

## 安装与版本

| 项 | 要求 |
|----|------|
| 客户端 | 安装最新版 WorkBuddy 桌面端 |
| Key | TokenHub（推荐）或 OpenRouter；若 TokenHub Key 为「限定范围」，需勾选 `hy3` |

## 配置项（TokenHub）

1. 启动 WorkBuddy → 左下角账户 → **设置**  
2. 左侧 **模型** → **自定义模型** → **添加模型**  
3. 提供商选择 **自定义 / Custom**  
4. 按 [`settings.tokenhub.json`](./settings.tokenhub.json) 填写：

| 字段 | 值 |
|------|-----|
| 接口地址 | `https://tokenhub.tencentmaas.com/v1/chat/completions` |
| API Key | TokenHub Key（见 `docs/integrations/.env` 中 `HY3_API_KEY`） |
| 模型名称 | `hy3` |
| 高级工具 | 建议勾选：工具调用、图片输入、推理模式 |

5. 保存后，在对话界面模型选择器中选 `hy3`。

> 注意：WorkBuddy 表单里的接口地址通常要写到 **`/v1/chat/completions` 完整路径**（与只写到 `/v1` 的 SDK 略有不同）。

## 配置项（OpenRouter）

对照 [`settings.openrouter.json`](./settings.openrouter.json)：

| 字段 | 值 |
|------|-----|
| 接口地址 | `https://openrouter.ai/api/v1/chat/completions` |
| API Key | `sk-or-...` |
| 模型名称 | `tencent/hy3` |

## 第一次对话

选择已添加的 Hy3，发送：`用三句话介绍你自己。`  
截图：`docs/integrations/assets/workbuddy-first-chat.png`

## 端到端任务 Demo

**任务：** 让 WorkBuddy 根据一段会议记录整理「决议 / 待办 / 风险」三条。  
截图：`docs/integrations/assets/workbuddy-meeting-demo.png`

## 注意事项

- 改完自定义模型后若列表不出现，**完全退出并重启** WorkBuddy。  
- 401：检查 Key；限定范围 Key 需包含 `hy3`。  
- 404：检查接口是否带 `/v1/chat/completions`。  
- 提交前运行：`bash docs/integrations/sanitize_secrets.sh`

## 截图清单

| 文件 | 内容 |
|------|------|
| `docs/integrations/assets/workbuddy-settings.png` | 自定义模型配置页（Key 打码） |
| `docs/integrations/assets/workbuddy-first-chat.png` | 第一次对话 |
| `docs/integrations/assets/workbuddy-meeting-demo.png` | 会议纪要任务 |
