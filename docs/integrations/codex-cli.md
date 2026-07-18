# Codex CLI × Hy3

[Codex CLI](https://github.com/openai/codex)（及兼容的终端 Coding Agent）可通过自定义 provider 把请求转到 OpenRouter / TokenHub 上的 Hy3。

## 安装与版本

| 项 | 要求 |
|----|------|
| Node / 运行时 | 按 Codex CLI 官方安装说明（常见为 npm 全局安装或官方安装脚本） |
| 配置文件 | `~/.codex/config.toml`（路径以当前版本为准） |
| 网络 | 可访问 OpenRouter 或 TokenHub |

安装示例（以官方文档为准，版本会变）：

```bash
npm i -g @openai/codex
codex --version
```

## 配置项

### OpenRouter（常见写法）

在 `~/.codex/config.toml` 中配置自定义 provider（字段名请对照你本机 Codex 版本文档；以下为常见 OpenAI 兼容形态）：

```toml
model = "tencent/hy3"
model_provider = "openrouter"

[model_providers.openrouter]
name = "OpenRouter"
base_url = "https://openrouter.ai/api/v1"
env_key = "OPENROUTER_API_KEY"
```

```bash
export OPENROUTER_API_KEY='sk-or-v1-xxxxxxxx'
```

### TokenHub

```toml
model = "hy3"
model_provider = "tokenhub"

[model_providers.tokenhub]
name = "Tencent TokenHub"
base_url = "https://tokenhub.tencentmaas.com/v1"
env_key = "HY3_API_KEY"
```

```bash
export HY3_API_KEY='sk-xxxxxxxx'
```

| 配置 | OpenRouter | TokenHub |
|------|------------|----------|
| base_url | `https://openrouter.ai/api/v1` | `https://tokenhub.tencentmaas.com/v1` |
| model | `tencent/hy3` | `hy3` |
| 鉴权 | 环境变量中的 Bearer Key | 同左 |
| 协议 | OpenAI Chat Completions | 同左 |

## 第一次对话

```bash
codex "用一句话介绍你自己，并说明当前是 Hy3。"
```

或进入交互模式后发送同样提示。确认回复正常且未报 401/model not found。

**截图：** `assets/codex-first-chat.png`

## 端到端任务 Demo

**任务：** 在空目录生成一个最小 FastAPI `GET /health` 项目。

```bash
mkdir /tmp/hy3-codex-demo && cd /tmp/hy3-codex-demo
codex "创建最小 FastAPI 应用：GET /health 返回 {\"status\":\"ok\"}，并写 README 说明如何 uvicorn 启动。完成后停止。"
```

验收：`uvicorn` 能启动且 `/health` 返回 ok。  
**截图：** `assets/codex-fastapi-demo.png`

## 注意事项

- `env_key` 指向的环境变量必须在**当前 shell** 已 export。
- OpenRouter 模型名含 `tencent/`；写错会 404。
- Agent 会改文件：先在空目录或 git 仓库中试验。
- 若工具调用失败，可降低权限模式或换 TokenHub 对比。
- 免费 OpenRouter 路由可能限流，遇到 429 等待后重试。

## 截图清单

| 文件 | 内容 |
|------|------|
| `assets/codex-config.png` | config.toml（无密钥） |
| `assets/codex-first-chat.png` | 第一次对话 |
| `assets/codex-fastapi-demo.png` | 生成的项目与 health 响应 |
