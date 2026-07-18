# 05 Reasoning Mode

## Introduction

Hy3 supports toggling chain-of-thought reasoning via a reasoning-mode switch. This example compares two modes:

- **Thinking disabled**: no chain-of-thought; gives the answer directly. Fast response, suitable for everyday chat.
- **Thinking enabled**: performs deep chain-of-thought reasoning, outputting the step-by-step reasoning process (`reasoning_content`) first, then the final answer (`content`). Suitable for math, code, and complex logic reasoning tasks.

The example uses the same simple math analysis problem, calls the model with thinking disabled and enabled respectively, and prints a comparison of the two `reasoning_content` (chain-of-thought) and `content` (final answer) results.

---

## Prerequisites

1. The Hy3 service is available (one of the two):
   - **Cloud TokenHub API**: base_url `https://tokenhub.tencentmaas.com/v1`; apply for an API Key in the [TokenHub console](https://console.cloud.tencent.com/tokenhub/apikey).
   - **Local vLLM / SGLang deployment**: base_url `http://127.0.0.1:8000/v1`.

2. **If you want `reasoning_content` to be separated out independently**:
   - Cloud TokenHub API: use the `thinking` parameter for automatic separation (already included in this example).
   - Local vLLM: add `--reasoning-parser hy_v3` at startup.
   - Local SGLang: add `--reasoning-parser hunyuan` at startup.

   If the local reasoning parser is not enabled, the reasoning content may be mixed into `content`, and the `reasoning_content` field will be empty.

3. Install dependencies:
   ```bash
   pip install openai
   ```

4. Configure connection info via environment variables (defaults suit a local deployment):
   ```bash
   set HY3_BASE_URL=http://127.0.0.1:8000/v1
   set HY3_API_KEY=EMPTY
   ```
   If using the cloud TokenHub API:
   ```bash
   set HY3_BASE_URL=https://tokenhub.tencentmaas.com/v1
   set HY3_API_KEY=sk-yourAPIKey
   ```

---

## Complete Request

```python
"""Hy3 Example 05: Reasoning mode comparison (no_think / low / high).

Sends dual-compatible parameters for local and cloud:
  - Cloud TokenHub: thinking:{type: enabled|disabled}
  - Local vLLM/SGLang: chat_template_kwargs.reasoning_effort (no_think|low|high)

When thinking is enabled, chain-of-thought appears in message.reasoning_content
(local requires --reasoning-parser hy_v3 / hunyuan).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common import (  # noqa: E402
    chat_completion,
    extract_reasoning_and_content,
    get_config,
    make_client,
)

PROMPT = (
    "小明有 5 个苹果，分给 3 个朋友每人 1 个，又买了 2 个，现在他还有几个苹果？请逐步分析。"
)

MODES = (
    ("no_think", "Mode 1: Thinking off (no_think) — direct answer"),
    ("low", "Mode 2: Light thinking (low)"),
    ("high", "Mode 3: Deep thinking (high)"),
)


def run_mode(client, reasoning: str, title: str):
    print("=" * 70)
    print(title)
    print("=" * 70)
    print(f"[User Question]\n{PROMPT}\n")

    # high mode can emit long CoT; give it more room
    max_tokens = 8192 if reasoning == "high" else 2048
    response = chat_completion(
        client,
        [{"role": "user", "content": PROMPT}],
        reasoning=reasoning,
        max_tokens=max_tokens,
    )
    message = response.choices[0].message
    reasoning_content, content = extract_reasoning_and_content(message)

    if reasoning_content:
        print("[Chain-of-thought reasoning_content]")
        print(reasoning_content)
        print()
    else:
        print(
            "[Chain-of-thought reasoning_content] "
            "(none; thinking disabled, or server has no reasoning parser)\n"
        )

    print("[Final answer content]")
    print(content)
    if response.usage:
        print(
            f"\n[Usage] prompt={response.usage.prompt_tokens} "
            f"completion={response.usage.completion_tokens} "
            f"total={response.usage.total_tokens}"
        )
    print()


def main():
    cfg = get_config()
    print(f"Connecting to {cfg['base_url']}  model={cfg['model']}")
    client = make_client()

    for mode, title in MODES:
        run_mode(client, mode, title)

    print("=" * 70)
    print("[Comparison summary]")
    print("=" * 70)
    print("no_think: direct answer, lowest latency — everyday chat.")
    print("low:      light chain-of-thought — structured / multi-constraint tasks.")
    print("high:     deep CoT — math / code / hard reasoning (raise max_tokens).")
    print()
    print("If reasoning_content is empty when thinking is on, check:")
    print("  - Cloud TokenHub: thinking parameter is already sent by common.build_extra_body")
    print("  - Local vLLM:   add --reasoning-parser hy_v3 at startup")
    print("  - Local SGLang: add --reasoning-parser hunyuan at startup")


if __name__ == "__main__":
    main()
```

---

## Complete Response Parsing

### 1. How the reasoning-mode switch is passed

How the reasoning switch is passed depends on the deployment. This example **sends both parameter forms** to be compatible with both local and cloud:

```python
extra_body={
    # Reasoning switch for the cloud TokenHub API
    "thinking": {"type": "enabled"},   # "enabled" on / "disabled" off
    # Reasoning-depth switch for local vLLM/SGLang deployment
    "chat_template_kwargs": {"reasoning_effort": "high"},  # "high" / "no_think"
}
```

- **Cloud TokenHub API** recognizes the `thinking` field and ignores `chat_template_kwargs`.
- **Local vLLM/SGLang** recognizes `chat_template_kwargs.reasoning_effort` and ignores `thinking`.
- Sending both sets of parameters at the same time does not interfere; one piece of code is compatible with both deployments.

### 2. The reasoning switch for the cloud TokenHub API

| `thinking.type` | Behavior | Suitable scenarios |
|:---|:---|:---|
| `"disabled"` | Respond directly; no chain-of-thought | Everyday chat, simple Q&A |
| `"enabled"`  | Deep chain-of-thought; separates out `reasoning_content` | Math, code, complex logic reasoning |

The cloud also supports a top-level `reasoning_effort` parameter to control reasoning depth (`low`/`high`, default `low`); see the [deep-reasoning docs](https://cloud.tencent.com/document/product/1823/131208).

### 3. The reasoning-depth switch for local deployment

| `reasoning_effort` | Behavior | Suitable scenarios |
|:---|:---|:---|
| `"no_think"` | Respond directly; no chain-of-thought (default) | Everyday chat, simple Q&A |
| `"low"`      | Lightweight chain-of-thought | Moderately complex analysis |
| `"high"`     | Deep chain-of-thought; more thorough reasoning | Math, code, complex logic reasoning |

### 4. Response fields: `reasoning_content` and `content`

After thinking is enabled, the response `message` contains two fields:

- **`reasoning_content`**: the chain-of-thought (CoT), i.e. the model's step-by-step reasoning process. It is an optional field.
  - Cloud TokenHub API: auto-separated when the `thinking` parameter is used.
  - Local: requires the server to enable a reasoning parser (vLLM `--reasoning-parser hy_v3`; SGLang `--reasoning-parser hunyuan`).
- **`content`**: the final answer for the user.

Read it with compatibility handling (because `reasoning_content` may be `None`):

```python
reasoning_content = getattr(message, "reasoning_content", None)
if reasoning_content:
    print(reasoning_content)  # chain-of-thought
print(message.content)        # final answer
```

> If the local reasoning parser is not enabled, the reasoning process may be mixed into `content`, and `reasoning_content` will be empty.

### 5. Scenario recommendations

- **Thinking enabled**: math computation, code generation & debugging, multi-step logic reasoning, complex planning tasks. Reasoning is more thorough, but response time is longer and token consumption higher.
- **Thinking disabled**: chitchat, information lookup, formatted output, latency-sensitive scenarios. Fast response, low cost.

This example uses `temperature=0.9` and `top_p=1.0` (officially recommended params).

---

## Sample Output
> Verified live on **Tencent Cloud TokenHub** (`https://tokenhub.tencentmaas.com/v1`, `model=hy3`) on **2026-07-18**. Output is model-generated and may vary; secrets redacted.

```text
Mode: high (thinking enabled)
Final answer content: 4
reasoning_content present: True (len=89)
reasoning_content preview:
小明有5个苹果。 分给3个朋友每人1个，分出去3个，剩下 5 - 3 = 2 个。 又买了2个，现在有 2 + 2 = 4 个。 题目问还有几个，只给数字答案。 所以答案是 4。
```
