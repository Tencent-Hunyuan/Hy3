# Run Hy3 Locally

This page documents the repository's local-server option. The verified tool guides use Tencent Cloud TokenHub unless stated otherwise.

The root README documents deploying Hy3 with vLLM or SGLang first, then calling the OpenAI-compatible API.

> **Hardware feasibility:** Hy3 has 295B total parameters. The official deployment guidance recommends H20-3e cards or other GPUs with larger memory capacity when serving on eight GPUs. Confirm hardware, backend, and dependency requirements in the root [Deployment](../../README.md#deployment) section before choosing local mode; this is not a typical single-workstation setup.

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

- Follow the root README for hardware, backend, and dependency details; the commands above do not reduce the 295B model's serving requirements.
- Local self-hosted tool-by-tool verification is not part of this PR.
- TokenHub client integrations are covered in the tool-specific guides.
