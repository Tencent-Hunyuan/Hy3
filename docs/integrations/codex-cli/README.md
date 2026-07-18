# Codex CLI × Hy3

**以下命令均以仓库根目录** `Hy3/` **为当前目录执行。**

## 本目录文件


| 文件                                                                               | 用途                                    |
| -------------------------------------------------------------------------------- | ------------------------------------- |
| `[docs/integrations/codex-cli/config.tokenhub.toml](./config.tokenhub.toml)`     | TokenHub → 复制到 `~/.codex/config.toml` |
| `[docs/integrations/codex-cli/config.openrouter.toml](./config.openrouter.toml)` | OpenRouter 版                          |
| `[docs/integrations/codex-cli/run.sh](./run.sh)`                                 | 自动加载 `.env` 并启动 codex                 |


```bash
bash docs/integrations/sync_env.sh

# 推荐：一键运行（内部会 source .env）
bash docs/integrations/codex-cli/run.sh "用一句话介绍你自己，并说明当前是 Hy3。"

# 或手动：
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


| 配置       | OpenRouter                     | TokenHub                              |
| -------- | ------------------------------ | ------------------------------------- |
| base_url | `https://openrouter.ai/api/v1` | `https://tokenhub.tencentmaas.com/v1` |
| model    | `tencent/hy3`                  | `hy3`                                 |
| env_key  | `OPENROUTER_API_KEY`           | `HY3_API_KEY`                         |




## 端到端 Demo

空目录生成最小 FastAPI `GET /health`。截图：`docs/integrations/assets/codex-fastapi-demo.png`。

## 提交前

```bash
bash docs/integrations/sanitize_secrets.sh
```



## 注意事项

- `Model metadata for hy3 not found` 多为警告，Key 正确通常仍可调用。
- 勿把含真实 Key 的文件强制 `git add -f`。

