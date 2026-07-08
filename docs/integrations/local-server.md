# Run Hy3 Locally

The integration guides assume that Hy3 is running as a local OpenAI-compatible chat completions server.

The root README documents deploying Hy3 with vLLM or SGLang first, then calling the OpenAI-compatible API.

## Local API Settings

| Setting | Value |
|:---|:---|
| Base URL | `http://127.0.0.1:8000/v1` |
| Model | `hy3` |
| API key for local testing | `EMPTY` |
| API protocol | OpenAI-compatible chat completions |

## vLLM

The root README documents this vLLM server example with MTP enabled:

```bash
export VLLM_FLASHINFER_ALLREDUCE_BACKEND=trtllm
vllm serve tencent/Hy3 \
  --tensor-parallel-size 8 \
  --speculative-config.method mtp \
  --speculative-config.num_speculative_tokens 2 \
  --tool-call-parser hy_v3 \
  --reasoning-parser hy_v3 \
  --enable-auto-tool-choice \
  --port 8000 \
  --served-model-name hy3
```

## SGLang

The root README documents this SGLang server example with MTP enabled:

```bash
python3 -m sglang.launch_server \
  --model tencent/Hy3 \
  --tp-size 8 \
  --tool-call-parser hunyuan \
  --reasoning-parser hunyuan \
  --speculative-num-steps 2 \
  --speculative-eagle-topk 1 \
  --speculative-num-draft-tokens 3 \
  --speculative-algorithm EAGLE \
  --port 8000 \
  --served-model-name hy3
```

## Notes

- Follow the root README for hardware, backend, and dependency details.
- The tool guides in this directory have not yet been manually verified.
- Client-specific UI paths, exact versions, first-chat output, real task demo results, and screenshots/GIFs must be verified manually.
