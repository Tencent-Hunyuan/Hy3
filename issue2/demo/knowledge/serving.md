# Hy3 推理与 Agent 部署

Source: https://github.com/Tencent-Hunyuan/Hy3/blob/rhinobird2026/README_CN.md

Hy3 可通过 vLLM 或 SGLang 部署成 OpenAI 兼容 API。官方说明 8 卡部署建议使用 H20-3e 或其他具有更大显存的卡型。

vLLM 启动 Agent 工具调用时需要 `--tool-call-parser hy_v3`、`--reasoning-parser hy_v3` 和 `--enable-auto-tool-choice`。服务名可以用 `--served-model-name hy3` 固定为 hy3。

SGLang 对应使用 `--tool-call-parser hunyuan` 和 `--reasoning-parser hunyuan`。客户端应以实际 served model name 调用，并验证 `/chat/completions` 的真实响应。
