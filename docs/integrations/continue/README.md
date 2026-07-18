# Continue × Hy3

**以下命令均以仓库根目录 `Hy3/` 为当前目录执行。**

## 本目录文件

| 文件 | 用途 |
|------|------|
| [`docs/integrations/continue/config.tokenhub.yaml`](./config.tokenhub.yaml) | TokenHub |
| [`docs/integrations/continue/config.openrouter.yaml`](./config.openrouter.yaml) | OpenRouter |

```bash
bash docs/integrations/sync_env.sh
cp docs/integrations/continue/config.tokenhub.yaml ~/.continue/config.yaml
```

`sync_env.sh` 会把真实 Key 写入上述 yaml（仅本地）。**提交前必须**：

```bash
bash docs/integrations/sanitize_secrets.sh
```

截图：`docs/integrations/assets/continue-*.png`
