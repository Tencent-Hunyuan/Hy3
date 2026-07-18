# Codex CLI × Hy3

终端 Coding Agent，通过自定义 provider 使用 Hy3。  
**以下命令均以仓库根目录 `Hy3/` 为当前目录执行。**

## 本目录文件

| 文件 | 用途 |
|------|------|
| [`docs/integrations/codex-cli/config.openrouter.toml.example`](./config.openrouter.toml.example) | 复制为 `~/.codex/config.toml` |
| [`docs/integrations/codex-cli/config.tokenhub.toml.example`](./config.tokenhub.toml.example) | TokenHub 版 |
| [`docs/integrations/codex-cli/.env.example`](./.env.example) | 占位；真实值由 sync 生成 |

```bash
cp docs/integrations/.env.example docs/integrations/.env
# 编辑 docs/integrations/.env，填入 HY3_API_KEY
bash docs/integrations/sync_env.sh

set -a && source docs/integrations/codex-cli/.env && set +a
cp docs/integrations/codex-cli/config.tokenhub.toml ~/.codex/config.toml
codex "用一句话介绍你自己，并说明当前是 Hy3。"
```

## 安装

```bash
npm i -g @openai/codex
codex --version
```

## 配置对照

| 配置 | OpenRouter | TokenHub |
|------|------------|----------|
| base_url | `https://openrouter.ai/api/v1` | `https://tokenhub.tencentmaas.com/v1` |
| model | `tencent/hy3` | `hy3` |
| env_key | `OPENROUTER_API_KEY` | `HY3_API_KEY` |

## 端到端 Demo

空目录让 Codex 生成最小 FastAPI `GET /health`。  
截图：`docs/integrations/assets/codex-fastapi-demo.png`。

## 注意事项

- 环境变量必须在当前 shell 生效。
- Agent 会改文件，先在空目录试验。
- 勿提交真实 `.env` / 含 Key 的 config。
