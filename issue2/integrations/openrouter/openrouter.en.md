# Use Hy3 with OpenRouter

> 中文：[openrouter.md](openrouter.md) · [Back to index](../README.en.md)

OpenRouter is the simplest path when you do not want to operate an eight-GPU inference service. The fields below were checked against the [official Hy3 model page](https://openrouter.ai/tencent/hy3) on 2026-07-23.

## Requirements

- An OpenRouter account and API key
- `curl`, or Python 3.10+ for the showcase
- Model ID `tencent/hy3`; check the model page before relying on the optional `tencent/hy3:free` route

## Configuration

```bash
export HY3_PROVIDER=openrouter
export HY3_BASE_URL=https://openrouter.ai/api/v1
export HY3_MODEL=tencent/hy3
export HY3_API_KEY='sk-or-v1-...'
```

Never commit the key. OpenRouter exposes OpenAI-compatible `POST /chat/completions`; set reasoning depth with `reasoning.effort`.

## First conversation

```bash
curl "$HY3_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $HY3_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "tencent/hy3",
    "messages": [{"role": "user", "content": "Reply only with READY and your model ID."}],
    "temperature": 0.9,
    "reasoning": {"effort": "low"}
  }'
```

Accept only an HTTP 200 with a non-empty `choices[0].message.content`.

## End-to-end task: Evidence Board

1. Start the showcase from `issue2/demo` with `python3 server.py`.
2. Open `http://127.0.0.1:8765` and confirm the header says **Live Hy3**.
3. Ask the app to explain why Hy3 fits agent workflows and to cite its size, context length, and serving requirements.
4. Verify the trace contains a `search_knowledge_base` call followed by a final cited report.

Use `HY3_DEMO_MODE=1 python3 server.py` only for offline UI and retrieval checks. It is visibly marked and is not live-model evidence.

![Evidence Board offline screenshot](../../assets/evidence-board-offline.png)

## Troubleshooting

| Symptom | Check |
|:---|:---|
| `401` | Complete key, whitespace, and account credit |
| `404 model not found` | Use `tencent/hy3`, not the self-hosted name `hy3` |
| No tool call | Include `tools`, confirm route support, and retry a one-tool prompt |
| Slow output | Use low reasoning and a shorter prompt first |
| Unbounded spend | Add a key limit and inspect response `usage` |

Before submission, record a live clip under one minute showing model ID, prompt, tool trace, and report with the key hidden. This repository does not fabricate that online evidence.
