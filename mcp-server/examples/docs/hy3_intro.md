# Hy3 Model Overview

## Key specifications

Hy3 is Tencent Hunyuan's flagship open-source large language model. The
context length of Hy3 is 256K tokens, which enables long-document
understanding and stable multi-turn agent workflows. The model uses a
Mixture-of-Experts (MoE) architecture with 295B total parameters, of which
21B are active per token.

## Reasoning modes

Hy3 supports three reasoning effort levels: no_think, low and high. The
level is selected per request through chat_template_kwargs.reasoning_effort
on the OpenAI-compatible API. Higher effort improves complex reasoning at
the cost of latency; no_think is best for fast, factual tasks.

## Agent capabilities

Hy3 is optimized for agent scenarios: tool-call outputs are stable across
scaffoldings (the reported SWE-Bench variance across harnesses is below 4%),
and the hallucination rate was reduced from 12.5% to 5.4% relative to the
previous generation, which matters for grounded, citation-based answers.

## Serving

Hy3 can be served locally with vLLM or SGLang as an OpenAI-compatible
endpoint at http://127.0.0.1:8000/v1 with the served model name "hy3" and
any non-empty API key. The recommended sampling parameters are temperature
0.9 and top_p 1.0.
