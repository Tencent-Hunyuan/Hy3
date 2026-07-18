# Dify × Hy3

配置路径相对仓库根目录 `Hy3/`。

## 本目录文件

| 文件 | 用途 |
|------|------|
| [`docs/integrations/dify/provider.tokenhub.json`](./provider.tokenhub.json) | TokenHub 表单对照 |
| [`docs/integrations/dify/provider.openrouter.json`](./provider.openrouter.json) | OpenRouter 对照 |

```bash
bash docs/integrations/sync_env.sh
```

在 Dify UI：设置 → 模型供应商 → OpenAI-API-compatible，按 JSON 字段填写。

截图：`docs/integrations/assets/dify-*.png`

提交前：`bash docs/integrations/sanitize_secrets.sh`
