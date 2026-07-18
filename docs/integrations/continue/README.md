# Continue × Hy3

[Continue](https://continue.dev) 插件通过 OpenAI 兼容接口接入 Hy3。  
**以下命令均以仓库根目录 `Hy3/` 为当前目录执行。**

## 本目录文件

| 文件 | 用途 |
|------|------|
| [`docs/integrations/continue/config.openrouter.yaml.example`](./config.openrouter.yaml.example) | 合并/复制到 `~/.continue/config.yaml` |
| [`docs/integrations/continue/config.tokenhub.yaml.example`](./config.tokenhub.yaml.example) | TokenHub 版 |

```bash
cp docs/integrations/.env.example docs/integrations/.env
bash docs/integrations/sync_env.sh
# 若已填真实 HY3_API_KEY，会生成 docs/integrations/continue/config.tokenhub.yaml
cp docs/integrations/continue/config.tokenhub.yaml ~/.continue/config.yaml
# 或手动合并 example：
# cp docs/integrations/continue/config.tokenhub.yaml.example ~/.continue/config.yaml
```

若已有 Continue 配置，请**合并** `models:` 段，勿盲目整文件覆盖。

## 配置项

| 配置 | OpenRouter | TokenHub |
|------|------------|----------|
| apiBase | `https://openrouter.ai/api/v1` | `https://tokenhub.tencentmaas.com/v1` |
| model | `tencent/hy3` | `hy3` |
| provider | `openai` | `openai` |

## 第一次对话 / Demo

侧栏选 Hy3，解释当前文件；再对选中函数生成 docstring + pytest 草稿。  
截图见 `docs/integrations/assets/continue-*.png`。

## 注意事项

- `apiBase` 写到 `/v1`。
- 勿提交含真实 Key 的 config。
