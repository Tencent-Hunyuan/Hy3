# 在 Continue 中使用 Hy3

[Continue](https://www.continue.dev/) 是一款开源的 AI 编程助手，支持 VS Code、JetBrains 和任意文本编辑器。它原生支持 OpenAI-compatible 自定义模型，因此接入 Hy3 非常直接。

## 1. 安装与版本要求

- **VS Code**：≥ 1.80（Continue 同时支持 JetBrains，本文以 VS Code 为例）
- **Continue 插件**：在 VS Code 扩展商店搜索 `Continue` 并安装
- **网络**：能访问本地 vLLM/SGLang、OpenRouter 或 TokenHub
- **账号**：已有 Hy3 可用的 API Key

验证安装：安装完成后，VS Code 左侧边栏会出现 Continue 图标，快捷键 `Ctrl+L`（Windows/Linux）或 `Cmd+L`（macOS）可打开聊天面板。

## 2. 核心配置项

打开 Continue 配置文件：

- 点击 Continue 面板左下角的齿轮图标，选择 **Open config.json**。
- 或使用命令面板（`Ctrl+Shift+P`）搜索 `Continue: Open config.json`。

在 `models` 数组中添加 Hy3 配置：

```json
{
  "title": "Hy3 (OpenRouter)",
  "provider": "openai",
  "model": "tencent/hy3-295b-a21b",
  "apiKey": "${OPENROUTER_API_KEY}",
  "apiBase": "https://openrouter.ai/api/v1",
  "completionOptions": {
    "temperature": 0.9,
    "topP": 1.0,
    "maxTokens": 4096
  }
}
```

如果使用本地 vLLM/SGLang：

```json
{
  "title": "Hy3 (Local)",
  "provider": "openai",
  "model": "hy3",
  "apiKey": "EMPTY",
  "apiBase": "http://127.0.0.1:8000/v1",
  "completionOptions": {
    "temperature": 0.9,
    "topP": 1.0,
    "maxTokens": 4096
  }
}
```

| 配置项 | 说明 |
| --- | --- |
| `provider` | 必须填 `openai`，表示使用 OpenAI-compatible 协议 |
| `model` | 模型名，OpenRouter 填 `tencent/hy3-295b-a21b`，本地填 `hy3` |
| `apiBase` | Base URL，注意保留 `/v1` |
| `apiKey` | 对应服务商 API Key；本地部署可填 `EMPTY` |

> 建议不要把真实 API Key 写进 `config.json`。Continue 支持环境变量引用 `${VAR_NAME}`，把 Key 配置进系统环境变量更安全。

## 3. 第一次对话测试

1. 打开任意代码文件。
2. 按 `Ctrl+L` 打开 Continue 侧边栏。
3. 在模型下拉框中选择 **Hy3 (OpenRouter)**。
4. 输入：
   ```text
   请用一句话介绍 Hy3，并输出数字 1
   ```

预期结果：Continue 面板显示 Hy3 的回复。

![Continue + Hy3 示意图](./assets/continue.svg)

## 4. 端到端实战 Demo：解释并重构选中代码

1. 在编辑器中选中一段复杂函数。
2. 按 `Ctrl+L` 打开 Continue，输入：
   ```text
   请解释这段代码的功能，指出潜在问题，然后给出一个更简洁、可维护的重构版本。
   ```
3. Continue 会自动把当前选中的代码作为上下文发送给 Hy3。
4. Hy3 返回解释、问题列表和重构后的代码。
5. 点击 Continue 面板中的 **Apply** 按钮，可直接将重构代码写入文件。

示例输出：

```markdown
### 功能
该函数读取 CSV 文件并按日期聚合销售额。

### 潜在问题
1. 未处理文件不存在的情况。
2. 日期解析依赖系统 locale，可能因环境不同而失败。
3. 内存占用随 CSV 行数线性增长。

### 重构版本
```python
import pandas as pd
from pathlib import Path

def aggregate_sales(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(csv_path)
    df = pd.read_csv(csv_path, parse_dates=["date"], dayfirst=False)
    return df.groupby("date")["amount"].sum().reset_index()
```
```

## 5. 常见注意事项

1. **`apiBase` 末尾 `/v1`**：Continue 使用 OpenAI SDK，需要完整的 `/v1` 路径。如果填 `https://openrouter.ai/api` 会报 404。
2. **模型下拉框未出现**：保存 `config.json` 后，点击 Continue 面板顶部模型名刷新列表。
3. **Tab 自动补全**：Continue 的 Tab 自动补全默认使用 `tabAutocompleteModel`。如需使用 Hy3 补全，可单独配置：
   ```json
   "tabAutocompleteModel": {
     "title": "Hy3 Autocomplete",
     "provider": "openai",
     "model": "tencent/hy3-295b-a21b",
     "apiKey": "${OPENROUTER_API_KEY}",
     "apiBase": "https://openrouter.ai/api/v1"
   }
   ```
4. **上下文长度**：Continue 默认发送的上下文较小。如需利用 Hy3 的 256K 长上下文，可在 `config.json` 中调大 `contextLength`：
   ```json
   "contextLength": 128000
   ```
5. **流式输出**：Continue 默认开启流式，不建议关闭。
6. **本地部署工具调用**：如需在 Continue 中使用 Hy3 的 Agent 能力，本地 vLLM/SGLang 必须开启 `--tool-call-parser`。
