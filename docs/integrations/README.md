# Hy3 主流工具接入指南

> 面向终端用户：在常用 AI 产品里把 **Hy3** 用起来。  
> 对应犀牛鸟 Issue [#2](https://github.com/Tencent-Hunyuan/Hy3/issues/2)。  
> **以下命令均以仓库根目录 `Hy3/` 为当前目录执行。**

每个工具是一个**独立文件夹**：内含指南 `README.md` + 配置样例。

### 统一填写 Key（推荐）

只需维护 **一个** `docs/integrations/.env`，再同步到各子目录：

```bash
cp docs/integrations/.env.example docs/integrations/.env
# 编辑 docs/integrations/.env，填入 HY3_API_KEY / OPENROUTER_API_KEY
bash docs/integrations/sync_env.sh
```

| 文件 | 说明 |
|------|------|
| [`docs/integrations/.env.example`](./.env.example) | 模板（可提交） |
| `docs/integrations/.env` | 真实密钥（已 gitignore，勿提交） |
| [`docs/integrations/sync_env.sh`](./sync_env.sh) | 同步脚本 |

后端可选：

| 后端 | Base URL | Model | API Key |
|------|----------|-------|---------|
| [TokenHub](https://cloud.tencent.com/document/product/1823/132252) | `https://tokenhub.tencentmaas.com/v1` | `hy3` | TokenHub Key |
| [OpenRouter](https://openrouter.ai/tencent/hy3) | `https://openrouter.ai/api/v1` | `tencent/hy3` | `sk-or-...` |

> Cursor 走 OpenRouter 时，Base URL 常用 `https://openrouter.ai/api/v1/cursor`（见 [cursor/](./cursor/)）。

## 工具索引

| # | 工具 | 类型 | 目录 | 配置样例 |
|---|------|------|------|----------|
| 1 | OpenRouter | 聚合 API / 网页 | [openrouter/](./openrouter/) | `.env.example`、`curl_chat.sh`、`chat_example.py` |
| 2 | Cursor | AI IDE | [cursor/](./cursor/) | `settings.*.example.json` |
| 3 | Continue | VS Code / JetBrains | [continue/](./continue/) | `config.*.yaml.example` |
| 4 | Codex CLI | 终端 Agent | [codex-cli/](./codex-cli/) | `config.*.toml.example`、`.env.example` |
| 5 | Dify | 低代码 / Agent | [dify/](./dify/) | `provider.*.example.json`、`.env.example` |

## 小作品（Part B）

独立开源应用：**Hy3 Workbench**（网页 Agent 工作台，支持思考模式 + 工具调用）

- 仓库：<https://github.com/xianggkl/hy3-showcase>（推送后更新为你的实际地址）
- 能力：推理（`thinking` / `reasoning_effort`）、Function Calling、多轮工具回填
- 本地启动见该仓库 README；演示 GIF/视频放在仓库 `docs/demo.gif`

## 建议阅读顺序

1. [openrouter/](./openrouter/) — 先拿到一把通用 Key  
2. [cursor/](./cursor/) — IDE 里写代码  
3. [continue/](./continue/) — VS Code 轻量接入  
4. [codex-cli/](./codex-cli/) — 终端 Agent  
5. [dify/](./dify/) — 无代码搭 Agent  

## 截图说明

示意图见 [`docs/integrations/assets/`](./assets/)。请用本机真实界面截图（Key 打码）按各目录 README「截图清单」命名后放入该目录。
