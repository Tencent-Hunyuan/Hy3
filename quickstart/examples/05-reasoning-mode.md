# Example 5: Reasoning Mode

Hy3 supports **fast thinking** (direct response) and **slow thinking** (chain-of-thought reasoning). This example shows how to control reasoning mode and compare outputs.

## What You'll Learn

- Enable/disable reasoning mode with `reasoning_effort`
- Compare fast vs. deep thinking on the same prompt
- Access reasoning content in the response
- Know when to use each mode

---

## Reasoning Modes

| Mode | `reasoning_effort` | Mechanism | Best For | Approx. Tokens |
|:---|:---|:---|:---|:---|
| **Fast** | `"no_think"` | Direct generation | Chat, translation, summarization, simple Q&A | Baseline |
| **Light** | `"low"` | Brief chain-of-thought | Planning, analysis, moderate reasoning | +30-50% |
| **Deep** | `"high"` | Extensive chain-of-thought | Math proofs, complex coding, multi-step logic | +100-300% |

---

## Fast Thinking (Default)

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="EMPTY",
)

# Fast thinking — "no_think" is the default
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "What is 156 * 234?"}],
    temperature=0.9,
    top_p=1.0,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)

print(response.choices[0].message.content)
```

### Sample Output (Fast)

```
156 × 234 = 36,504.
```

---

## Deep Reasoning

```python
# Deep reasoning for complex tasks
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "Prove that the square root of 2 is irrational."}],
    temperature=0.9,
    top_p=1.0,
    max_tokens=1024,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}},
)

message = response.choices[0].message

# The thinking process
if hasattr(message, "reasoning_content") and message.reasoning_content:
    print("=== THINKING ===")
    print(message.reasoning_content)
    print()

print("=== ANSWER ===")
print(message.content)
```

### Sample Output (Deep Reasoning)

```
=== THINKING ===
We need to prove that √2 is irrational using proof by contradiction.

Assume √2 = a/b where a, b are coprime integers, b ≠ 0.
Then 2 = a²/b²
→ a² = 2b²
So a² is even, which means a is even.
Let a = 2k for some integer k.
Then (2k)² = 2b²
→ 4k² = 2b²
→ 2k² = b²
So b² is even, which means b is also even.
But this contradicts our assumption that a and b are coprime (both even means they share factor 2).
Therefore, our assumption is false, and √2 cannot be expressed as a ratio of integers.
Thus √2 is irrational.

=== ANSWER ===
Proof that √2 is irrational (by contradiction):

1. Assume √2 is rational: √2 = a/b where a, b are integers with no common factors, b ≠ 0.
2. Square both sides: 2 = a²/b² → a² = 2b².
3. a² is even → a is even. Write a = 2k.
4. Substitute: (2k)² = 2b² → 4k² = 2b² → 2k² = b².
5. b² is even → b is even.
6. Both a and b are even, contradicting that they have no common factors.
7. Therefore, the assumption is false. √2 is irrational. ∎
```

---

## Comparing Fast vs. Deep on the Same Prompt

```python
PROMPTS = [
    ("Math", "Solve: If 3x + 7 = 22, what is x?"),
    ("Logic", "All cats are mammals. All mammals are animals. Is a cat an animal? Explain."),
    ("Code", "Write a Python function to find the longest palindrome substring."),
    ("Creative", "Write a haiku about machine learning."),
]

modes = [
    ("no_think", "Fast"),
    ("high", "Deep"),
]

for category, prompt in PROMPTS:
    print(f"\n{'='*60}")
    print(f"CATEGORY: {category}")
    print(f"PROMPT: {prompt}")

    for effort, label in modes:
        response = client.chat.completions.create(
            model="hy3",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,
            top_p=1.0,
            max_tokens=512,
            extra_body={"chat_template_kwargs": {"reasoning_effort": effort}},
        )

        msg = response.choices[0].message
        thinking = getattr(msg, "reasoning_content", "") or ""
        content = msg.content or ""

        print(f"\n--- {label} Thinking ({effort}) ---")
        print(f"Tokens: {response.usage.total_tokens} "
              f"(prompt: {response.usage.prompt_tokens}, "
              f"completion: {response.usage.completion_tokens})")
        if thinking:
            print(f"Thinking chars: {len(thinking)}")
        print(f"Answer: {content[:200]}...")
```

### Sample Comparison Output

```
============================================================
CATEGORY: Math
PROMPT: Solve: If 3x + 7 = 22, what is x?

--- Fast Thinking (no_think) ---
Tokens: 28 (prompt: 18, completion: 10)
Answer: x = 5.

--- Deep Thinking (high) ---
Tokens: 72 (prompt: 18, completion: 54)
Thinking chars: 85
Answer: Let me solve this step by step: 3x + 7 = 22 → subtract 7 from both sides: 3x = 15 → divide by 3: x = 5.

============================================================
CATEGORY: Logic
PROMPT: All cats are mammals. All mammals are animals. Is a cat an animal? Explain.

--- Fast Thinking (no_think) ---
Tokens: 45 (prompt: 27, completion: 18)
Answer: Yes, a cat is an animal. By transitive property: cats → mammals → animals.

--- Deep Thinking (high) ---
Tokens: 150 (prompt: 27, completion: 123)
Thinking chars: 215
Answer: Yes. This is a syllogism. The transitive property of set membership states that if A ⊆ B and B ⊆ C, then A ⊆ C. Here: Cats ⊆ Mammals ⊆ Animals, therefore Cats ⊆ Animals. So every cat is an animal.
```

---

## When to Use Each Mode

### Use Fast Thinking (`"no_think"`) For:
- Casual conversation and chat
- Translation tasks
- Text summarization
- Simple factual queries
- When latency matters more than depth
- When token cost is a concern

### Use Deep Reasoning (`"high"`) For:
- Mathematical proofs and calculations
- Complex coding problems
- Multi-step logical reasoning
- Planning and strategy
- Analysis requiring structured thinking
- When accuracy > speed

### Use Light Reasoning (`"low"`) For:
- Moderate analysis tasks
- When you want some reasoning but don't need full depth
- Balancing speed and quality

---

## Accessing Reasoning Content in the Response

```python
message = response.choices[0].message

# The final answer
final_answer = message.content

# The thinking process (only with reasoning_effort="low" or "high")
thinking_process = getattr(message, "reasoning_content", None)

if thinking_process:
    print(f"Model thought for {len(thinking_process)} characters before answering.")
    print(f"Thinking: {thinking_process[:300]}...")
print(f"Answer: {final_answer}")
```

In streaming mode, reasoning content arrives in `delta.reasoning_content` before the final answer in `delta.content`. See [Example 2: Streaming](02-streaming.md) for details.

---

## Key Takeaways

1. **`reasoning_effort` is passed via `extra_body`**, not as a top-level parameter.
2. **Default is `"no_think"`** — the model answers directly without visible reasoning.
3. **Deep reasoning increases token usage** but dramatically improves accuracy on complex tasks.
4. **`reasoning_content`** contains the model's internal thinking — access it for transparency or debugging.
5. **Match the mode to the task** — don't use deep reasoning for simple chat; don't use fast thinking for math proofs.

---

## Run the Script

```bash
pip install openai
python 05-reasoning-mode.py
```
