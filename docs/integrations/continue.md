# Continue × Hy3

[Continue](https://continue.dev) 是 VS Code / JetBrains 的开源 AI 编程插件，可通过 OpenAI 兼容接口接入 Hy3。

## 安装与版本

| 项 | 要求 |
|----|------|
| 编辑器 | VS Code 1.90+ 或 JetBrains 近期版本 |
| 插件 | 市场搜索安装 **Continue** |
| 配置文件 | `~/.continue/config.yaml`（或 Continue 设置 UI） |
| Key | OpenRouter 或 TokenHub |

## 配置项

编辑 `~/.continue/config.yaml`（字段名以你安装的 Continue 版本为准，常见如下）：

### OpenRouter

```yaml
models:
  - name: Hy3 (OpenRouter)
    provider: openai
    model: tencent/hy3
    apiBase: https://openrouter.ai/api/v1
    apiKey: sk-or-v1-xxxxxxxx
```

### TokenHub

```yaml
models:
  - name: Hy3 (TokenHub)
    provider: openai
    model: hy3
    apiBase: https://tokenhub.tencentmaas.com/v1
    apiKey: sk-xxxxxxxx
```

| 配置 | OpenRouter | TokenHub |
|------|------------|----------|
| apiBase | `https://openrouter.ai/api/v1` | `https://tokenhub.tencentmaas.com/v1` |
| model | `tencent/hy3` | `hy3` |
| provider | `openai`（兼容模式） | 同左 |
| 协议 | Chat Completions | 同左 |

保存后在 Continue 面板下拉选择 **Hy3**。

## 第一次对话

1. 打开 Continue 侧栏。
2. 选中 Hy3。
3. 发送：`解释当前打开文件的第一段代码在做什么（简体中文）。`
4. 确认回答与文件内容相关。

**截图：** `assets/continue-first-chat.png`

## 端到端任务 Demo

**任务：** 选中一段函数，用 Continue 的 edit/inline 能力生成 docstring + 一个单元测试草稿。

1. 选中代码 → Continue 「edit」或聊天中附带代码引用。  
2. 提示：`为选中函数补充 Google 风格 docstring，并给出 pytest 用例草稿。`  
3. 将结果粘贴/应用后本地跑测试。

**截图：** `assets/continue-edit-demo.png`

## 注意事项

- `apiBase` 一般**不要**加 `/chat/completions` 后缀，只写到 `/v1`。
- OpenRouter 模型名带 `tencent/` 前缀；TokenHub 用 `hy3`。
- Key 可用环境变量引用（若版本支持），避免明文提交 `config.yaml` 到 Git。
- 若 401：检查 Continuue 是否读到了正确的 `apiKey`（有时需重载窗口）。
- 上下文过长时先缩小选区，避免触及套餐 TPM。

## 截图清单

| 文件 | 内容 |
|------|------|
| `assets/continue-config.png` | config.yaml 或设置页（Key 打码） |
| `assets/continue-first-chat.png` | 第一次对话 |
| `assets/continue-edit-demo.png` | 编辑/补全任务结果 |
