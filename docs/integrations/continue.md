# Hy3 with Continue (VS Code)

[Continue](https://continue.dev/) 是开源的 VS Code / JetBrains AI 编程助手，支持自定义模型配置。

## 1. 安装与版本要求

- VS Code ≥ 1.78
- 扩展 `continue.continue`（已验证版本 **v2.0.0**）

```bash
code --install-extension continue.continue
```

- 本地或云端已部署 Hy3 服务

## 2. 配置项

| 配置项 | 值 |
|--------|-----|
| 协议 | OpenAI 兼容 |
| provider | `openai` |
| model | `hy3` |
| apiBase | `http://127.0.0.1:8000/v1`（本地） |
| apiKey | `EMPTY`（本地） |
| 配置入口 | `~/.continue/config.json`（本机已配置） |

### 本机已写入配置

`~/.continue/config.json`：

```json
{
  "models": [
    { "title": "Hy3", "provider": "openai", "model": "hy3",
      "apiBase": "http://127.0.0.1:8000/v1", "apiKey": "EMPTY" }
  ]
}
```

## 3. 端到端流程

### 步骤 1：配置

按上文写入 `~/.continue/config.json`，重启 VS Code。

### 步骤 2：第一次对话

点击侧边栏 Continue 图标 → Chat 输入「你好」验证连通。

### 步骤 3：跑通一个真实任务

```
解释这段 Python 代码的时间复杂度，并给出优化建议：
`[x for x in a if x in b]`
```

Continue 调用 Hy3 给出分析，可直接用于编辑器内联。

## 4. 端到端 demo（截图 / GIF）

> 截图位置：见 [screenshots 指南](../../screenshots/README.md)
> - 图 1：Continue 模型列表（含 Hy3）
> - 图 2：第一次对话
> - 图 3：真实任务（代码分析）

## 5. 常见注意事项

- 修改 `config.json` 后需重启 VS Code 生效
- 支持 tab 自动补全（需单独配置 `tabAutocompleteModel`）
- 多模型可并存，通过 `@` 切换
- 本地部署 tool calling 需 Hy3 启用 `--enable-auto-tool-choice`
