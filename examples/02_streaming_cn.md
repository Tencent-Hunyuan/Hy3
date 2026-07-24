# 02 流式输出

使用 Chat Completions API 逐个读取流式 chunk，并在最后读取 usage。

## 运行

```bash
uv run --env-file .env python examples/02_streaming.py
```

## 请求和解析

请求设置 `stream: true` 和 `stream_options.include_usage: true`。

脚本检查 `chunk.choices` 是否为空，再读取 `chunk.choices[0].delta.content`；最后一个 usage chunk 可能没有 choices，但会包含 `chunk.usage`。

## 输出示例

```text
深圳是中国南部海滨的现代化大都市，也是改革开放后迅速崛起的经济特区和创新之都。这里拥有华为、腾讯等科技巨头，以及完善的产业链，被誉为“中国硅谷”。作为移民城市和粤港澳大湾区核心引擎，深圳以高效、年轻和包容的姿态持续吸引着全球人才与资本。

usage: CompletionUsage(completion_tokens=62, prompt_tokens=21, total_tokens=83, completion_tokens_details=CompletionTokensDetails(accepted_prediction_tokens=None, audio_tokens=None, reasoning_tokens=0, rejected_prediction_tokens=None), prompt_tokens_details=PromptTokensDetails(audio_tokens=None, cache_write_tokens=None, cached_tokens=0))
```

流式文本会随着事件到达逐步打印，完整输出和 Token 统计可能不同。
