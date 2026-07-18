# Dify × Hy3

[Dify](https://dify.ai) 低代码平台，将 Hy3 加为 OpenAI 兼容模型后可搭聊天 / Agent。

## 本目录文件

| 文件 | 用途 |
|------|------|
| [`provider.tokenhub.example.json`](./provider.tokenhub.example.json) | 供应商表单对照（TokenHub） |
| [`provider.openrouter.example.json`](./provider.openrouter.example.json) | OpenRouter 对照 |
| [`.env.example`](./.env.example) | 本地记录 Key（勿提交真实值） |

> 在 Dify **Web UI** 填写；JSON 仅作字段对照。

## 配置对照

| 配置 | TokenHub | OpenRouter |
|------|----------|------------|
| API Endpoint | `https://tokenhub.tencentmaas.com/v1` | `https://openrouter.ai/api/v1` |
| Model Name | `hy3` | `tencent/hy3` |

路径：`设置` → `模型供应商` → OpenAI-API-compatible。

## Demo

会议纪要提炼 Chatflow；截图：`../assets/dify-meeting-demo.png`。

## 注意事项

- Endpoint 一般填到 `/v1`。
- 导出应用前去掉密钥。
