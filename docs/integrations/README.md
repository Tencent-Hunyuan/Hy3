# Hy3 主流工具接入指南

> 面向终端用户：在常用 AI 产品里把 **Hy3** 用起来。  
> 对应犀牛鸟 Issue [#2](https://github.com/Tencent-Hunyuan/Hy3/issues/2)。  
> **以下命令均以仓库根目录 `Hy3/` 为当前目录执行。**

每个工具一个文件夹：指南 + **可直接使用的配置文件**。

### 密钥与同步

```bash
bash docs/integrations/sync_env.sh
# 编辑 docs/integrations/.env 填入 Key 后再跑一次 sync
```

`.env` 建议字段：

```bash
HY3_API_KEY=...
HY3_BASE_URL=https://tokenhub.tencentmaas.com/v1
HY3_MODEL=hy3
OPENROUTER_API_KEY=...
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=tencent/hy3
```

1. `sync_env.sh`：把 Key 同步到各子目录 `.env`，并注入 WorkBuddy 等本地对照配置。  
2. **提交前**脱敏：

```bash
bash docs/integrations/sanitize_secrets.sh
git add docs/integrations
git commit -m "..."
```

| 脚本 | 作用 |
|------|------|
| [`docs/integrations/sync_env.sh`](./sync_env.sh) | 本地：分发 Key |
| [`docs/integrations/sanitize_secrets.sh`](./sanitize_secrets.sh) | 提交前：去除隐私 |

后端可选：

| 后端 | Base URL | Model | API Key |
|------|----------|-------|---------|
| [TokenHub](https://cloud.tencent.com/document/product/1823/132252) | `https://tokenhub.tencentmaas.com/v1` | `hy3` | TokenHub Key |
| [OpenRouter](https://openrouter.ai/tencent/hy3) | `https://openrouter.ai/api/v1` | `tencent/hy3` | `sk-or-...` |

> Cursor 走 OpenRouter 时 Base URL 常用 `https://openrouter.ai/api/v1/cursor`（见 [cursor/](./cursor/)）。  
> WorkBuddy 自定义模型接口地址通常要写到 `/v1/chat/completions`（见 [workbuddy/](./workbuddy/)）。

## 工具索引

| # | 工具 | 目录 | 主要配置 |
|---|------|------|----------|
| 1 | OpenRouter | [openrouter/](./openrouter/) | `curl_chat.sh`、`chat.py` |
| 2 | Cursor | [cursor/](./cursor/) | `settings.*.json` |
| 3 | WorkBuddy | [workbuddy/](./workbuddy/) | `settings.*.json` |
| 4 | Codex CLI | [codex-cli/](./codex-cli/) | `config.*.toml`、`run.sh` |
| 5 | Dify | [dify/](./dify/) | `provider.*.json` |

## 小作品（Part B）

独立开源应用：**Hy3 Workbench** — <https://github.com/xianggkl/hy3-showcase>

## 建议阅读顺序

1. [openrouter/](./openrouter/)  
2. [cursor/](./cursor/)  
3. [workbuddy/](./workbuddy/)  
4. [codex-cli/](./codex-cli/)  
5. [dify/](./dify/)  

## 截图说明

截图放入 [`docs/integrations/assets/`](./assets/)，文件名见各目录 README。
