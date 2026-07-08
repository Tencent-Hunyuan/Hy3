# Hy3 with Aider

[Aider](https://aider.chat/) 是终端下的 AI 编程助手，支持接任何 OpenAI 兼容的 API。

## 安装

```bash
pip install aider-chat
```

当前版本：aider-chat 0.86.2。

## 配置

### 方式一：环境变量

```bash
# 本地部署
export OPENAI_API_BASE=http://127.0.0.1:8000/v1
export OPENAI_API_KEY=EMPTY
export AIDER_MODEL=openai/hy3

# OpenRouter
export OPENAI_API_BASE=https://openrouter.ai/api/v1
export OPENAI_API_KEY=sk-or-v1-xxx
export AIDER_MODEL=openai/tencent/hy3
```

### 方式二：配置文件

创建 `~/.aider.conf.yml`：

```yaml
openai-api-base: http://127.0.0.1:8000/v1
openai-api-key: EMPTY
model: openai/hy3
```

## 使用

```bash
# 在项目目录启动
cd my-project
aider

# 指定文件
aider src/main.py src/utils.py

# 纯聊天模式（不修改文件）
aider --chat-mode
```

### 示例

```
> 给这个 Flask 应用添加用户认证功能，使用 JWT token
```

Aider 会调用 Hy3 生成代码并自动编辑文件。

## 常见参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--model` | 指定模型 | `openai/hy3` |
| `--openai-api-base` | API 地址 | `http://127.0.0.1:8000/v1` |
| `--openai-api-key` | API Key | `EMPTY` |
| `--edit-format` | 编辑格式 | `diff` / `udiff` / `search-replace` |
| `--no-auto-commits` | 不自动 commit | |
| `--yes` | 自动确认所有操作 | |

## 注意事项

- Aider 依赖 tool calling 执行文件编辑，确保 Hy3 支持 tool calling
- 如果遇到编辑失败，尝试 `--edit-format diff`
- `--model` 参数格式固定为 `openai/<model_name>`
- 建议配合 Git 使用，方便查看修改历史

## 截图

详见 [截图指南](../../screenshots/README.md#6-aider-终端)。
