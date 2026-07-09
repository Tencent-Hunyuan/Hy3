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
"""
Hy3 Reasoning Mode Comparison Example
=====================================

Demonstrates toggling Hy3's reasoning mode via the thinking switch, comparing two modes:
  - Thinking disabled: respond directly without chain-of-thought (suitable for everyday chat)
  - Thinking enabled: deep chain-of-thought reasoning, suitable for math/code/complex reasoning tasks

How the reasoning switch is passed depends on the deployment. This example sends both
parameter forms for compatibility:
  - Cloud TokenHub API: extra_body={"thinking": {"type": "enabled"|"disabled"}}
  - Local vLLM/SGLang deployment: extra_body={"chat_template_kwargs": {"reasoning_effort": "high"|"no_think"}}

When thinking is enabled, the response returns the chain-of-thought (CoT) in the
message.reasoning_content field, and the final answer in message.content.
  - Cloud: reasoning_content is auto-separated by the TokenHub API
  - Local: requires the server to enable a reasoning parser (vLLM: --reasoning-parser hy_v3; SGLang: --reasoning-parser hunyuan)

Connection info is configured via environment variables (with defaults):
  HY3_BASE_URL  default http://127.0.0.1:8000/v1
  HY3_API_KEY   default EMPTY
"""

import os

from openai import OpenAI

# Initialize the client via environment variables (with defaults) for easy deployment switching
client = OpenAI(
    base_url=os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
    api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
)

MODEL = "hy3"

# A prompt well-suited to triggering reasoning: a step-by-step analysis problem with simple arithmetic
PROMPT = "小明有 5 个苹果，分给 3 个朋友每人 1 个，又买了 2 个，现在他还有几个苹果？请逐步分析。"


def chat(enable_thinking: bool):
    """Call Hy3 with the specified reasoning mode and return the full message object.

    Sends both thinking (cloud TokenHub) and chat_template_kwargs.reasoning_effort
    (local vLLM/SGLang) parameter sets for local/cloud compatibility:
      - Cloud recognizes thinking; local ignores that field
      - Local recognizes chat_template_kwargs.reasoning_effort; cloud ignores that field
    """
    thinking_type = "enabled" if enable_thinking else "disabled"
    reasoning_effort = "high" if enable_thinking else "no_think"
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT}],
        temperature=0.9,
        top_p=1.0,
        extra_body={
            # Reasoning switch for the cloud TokenHub API
            "thinking": {"type": thinking_type},
            # Reasoning-depth switch for local vLLM/SGLang deployment
            "chat_template_kwargs": {"reasoning_effort": reasoning_effort},
        },
    )
    return response.choices[0].message


def print_section(title, message):
    """Uniformly print the reasoning_content (if any) and content of a call."""
    print("=" * 70)
    print(title)
    print("=" * 70)
    print(f"[User Question]\n{PROMPT}\n")

    # reasoning_content is an optional field: returns the chain-of-thought when thinking is enabled
    reasoning_content = getattr(message, "reasoning_content", None)
    if reasoning_content:
        print("[Chain-of-thought reasoning_content]")
        print(reasoning_content)
        print()
    else:
        print("[Chain-of-thought reasoning_content] (none; thinking disabled or server did not enable a reasoning parser)\n")

    print("[Final answer content]")
    print(message.content)
    print()


def main():
    # ---- Call 1: thinking disabled, respond directly ----
    msg_off = chat(enable_thinking=False)
    print_section("Mode 1: Thinking disabled (thinking: disabled / reasoning_effort: no_think)", msg_off)

    # ---- Call 2: thinking enabled, deep chain-of-thought ----
    msg_on = chat(enable_thinking=True)
    print_section("Mode 2: Thinking enabled (thinking: enabled / reasoning_effort: high)", msg_on)

    # ---- Comparison summary ----
    print("=" * 70)
    print("[Comparison summary]")
    print("=" * 70)
    print("Thinking disabled: gives the answer directly with no chain-of-thought; fast response, suitable for everyday chat.")
    print("Thinking enabled: outputs step-by-step reasoning (reasoning_content) first, then the final answer,")
    print("          suitable for math/code/complex logic reasoning tasks.")
    print()
    print("Tip: If reasoning_content is still empty when thinking is enabled, please verify:")
    print("  - Cloud TokenHub API: use the thinking parameter (already included in this example)")
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

> The following is sample output (not a real run result) to illustrate the print layout and differences between the two modes.

```text
======================================================================
Mode 1: Thinking disabled (thinking: disabled / reasoning_effort: no_think)
======================================================================
[User Question]
小明有 5 个苹果，分给 3 个朋友每人 1 个，又买了 2 个，现在他还有几个苹果？请逐步分析。

[Chain-of-thought reasoning_content] (none; thinking disabled or server did not enable a reasoning parser)

[Final answer content]
我们一步一步来分析：

1. **原有苹果数量**：小明一开始有 **5 个苹果**。
2. **分给朋友**：他分给 3 个朋友，每人 1 个，共分出 3 × 1 = 3 个苹果。
   此时小明剩下：5 - 3 = 2 个苹果。
3. **又买了苹果**：他又买了 2 个苹果，所以现在共有：2 + 2 = 4 个苹果。

**结论**：小明现在还有 **4 个苹果**。

======================================================================
Mode 2: Thinking enabled (thinking: enabled / reasoning_effort: high)
======================================================================
[User Question]
小明有 5 个苹果，分给 3 个朋友每人 1 个，又买了 2 个，现在他还有几个苹果？请逐步分析。

[Chain-of-thought reasoning_content]
用户问：小明有 5 个苹果，分给 3 个朋友每人 1 个，又买了 2 个，现在他还有几个苹果？请逐步分析。

我们需要计算一下：
初始：5个苹果
分给3个朋友每人1个：分出去3个，剩下 5 - 3 = 2 个
又买了2个：2 + 2 = 4 个

所以现在他有4个苹果。

逐步分析：
1. 初始状态：小明有 5 个苹果。
2. 分配过程：分给 3 个朋友，每人 1 个，共分出 3 × 1 = 3 个苹果。小明剩下的苹果数 = 5 - 3 = 2 个。
3. 购买过程：小明又买了 2 个苹果，此时苹果数 = 2 + 2 = 4 个。
4. 结论：小明现在还有 4 个苹果。

[Final answer content]
我们可以一步一步来分析这道题：

1. **初始数量**：小明最开始有 **5 个苹果**。
2. **分出去的数量**：小明分给 3 个朋友，每人 1 个，也就是分出去了 3 × 1 = **3 个苹果**。
   分完后，小明剩下的苹果数量是：5 - 3 = **2 个苹果**。
3. **新买的数量**：之后小明又买了 **2 个苹果**，这些苹果加到他剩下的苹果中。
   现在小明拥有的苹果数量是：2 + 2 = **4 个苹果**。

**结论**：经过分出去和重新购买后，小明现在还有 **4 个苹果**。

======================================================================
[Comparison summary]
======================================================================
Thinking disabled: gives the answer directly with no chain-of-thought; fast response, suitable for everyday chat.
Thinking enabled: outputs step-by-step reasoning (reasoning_content) first, then the final answer,
          suitable for math/code/complex logic reasoning tasks.

Tip: If reasoning_content is still empty when thinking is enabled, please verify:
  - Cloud TokenHub API: use the thinking parameter (already included in this example)
  - Local vLLM:   add --reasoning-parser hy_v3 at startup
  - Local SGLang: add --reasoning-parser hunyuan at startup
```
