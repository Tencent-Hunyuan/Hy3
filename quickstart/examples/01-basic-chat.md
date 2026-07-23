# Example 1: Basic Chat

Single-turn and multi-turn conversations with Hy3.

## What You'll Learn

- Send a single-turn chat request
- Build a multi-turn conversation with history
- Parse the response and extract content
- Understand `finish_reason`

---

## Single-Turn Chat

### Request

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="EMPTY",
)

response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "Explain quantum computing in one paragraph."},
    ],
    temperature=0.9,
    top_p=1.0,
    max_tokens=256,
)
```

### Response Parsing

```python
# Extract the assistant's reply
message = response.choices[0].message
content = message.content
finish_reason = response.choices[0].finish_reason

print(f"Role: {message.role}")
print(f"Content: {content}")
print(f"Finish reason: {finish_reason}")
print(f"Tokens used: {response.usage.total_tokens}")

# Check if the response was truncated
if finish_reason == "length":
    print("⚠️  Response was truncated — increase max_tokens.")
```

### Full Response Object (reference)

```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1719000000,
  "model": "hy3",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Quantum computing leverages the principles of quantum mechanics—superposition, entanglement, and interference—to process information in ways that classical computers cannot. Unlike classical bits that are either 0 or 1, quantum bits (qubits) can exist in multiple states simultaneously, enabling quantum computers to explore vast solution spaces in parallel. This makes them potentially transformative for problems like factoring large numbers, simulating molecular interactions for drug discovery, optimizing complex logistics, and enhancing machine learning. However, current quantum computers are still in the noisy intermediate-scale quantum (NISQ) era, with limited qubit counts and high error rates, requiring significant advances in error correction and hardware stability before they can achieve practical, large-scale quantum advantage.",
        "tool_calls": null
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 13,
    "completion_tokens": 129,
    "total_tokens": 142
  }
}
```

### Sample Output

```
Role: assistant
Content: Quantum computing leverages the principles of quantum mechanics...
Finish reason: stop
Tokens used: 142
```

---

## Multi-Turn Chat

Maintain conversation context by appending each response to the message history.

### Request

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="EMPTY",
)

# Initialize conversation with a system message (optional)
messages = [
    {
        "role": "system",
        "content": "You are a helpful physics tutor. Keep explanations concise.",
    },
]

# Turn 1
messages.append({"role": "user", "content": "What is quantum entanglement?"})

response = client.chat.completions.create(
    model="hy3",
    messages=messages,
    temperature=0.9,
    top_p=1.0,
    max_tokens=256,
)

reply_1 = response.choices[0].message.content
print(f"Assistant: {reply_1}\n")

# Add the assistant's response to history
messages.append({"role": "assistant", "content": reply_1})

# Turn 2 — model remembers context from Turn 1
messages.append({"role": "user", "content": "Can you give a real-world analogy for that?"})

response = client.chat.completions.create(
    model="hy3",
    messages=messages,
    temperature=0.9,
    top_p=1.0,
    max_tokens=256,
)

reply_2 = response.choices[0].message.content
print(f"Assistant: {reply_2}")
```

### Response Parsing

```python
def chat_turn(messages, user_input):
    """Send a message and return the assistant's reply, updating history."""
    messages.append({"role": "user", "content": user_input})

    response = client.chat.completions.create(
        model="hy3",
        messages=messages,
        temperature=0.9,
        top_p=1.0,
        max_tokens=512,
    )

    reply = response.choices[0].message.content
    messages.append({"role": "assistant", "content": reply})
    return reply


# Usage
messages = []
print("Turn 1:", chat_turn(messages, "What is a black hole?"))
print("Turn 2:", chat_turn(messages, "How big can they get?"))
print("Turn 3:", chat_turn(messages, "What happens if you fall into one?"))
```

### Sample Output

```
Turn 1: A black hole is a region of spacetime where gravity is so intense
that nothing, not even light, can escape. It forms when a massive star
collapses under its own gravity at the end of its life cycle...

Turn 2: Black holes vary enormously in size. Stellar-mass black holes are
typically 3 to tens of solar masses. Supermassive black holes at galactic
centers can reach millions or billions of solar masses—Sagittarius A* in
our Milky Way is about 4 million solar masses, while TON 618 is estimated
at 66 billion solar masses...

Turn 3: If you fell into a black hole, you'd experience "spaghettification"
— the tidal forces would stretch you vertically and compress you
horizontally as you approach the singularity. To an outside observer, you'd
appear to slow down and redshift, never quite crossing the event horizon,
due to extreme time dilation...
```

---

## Key Takeaways

1. **Append each response** to `messages` to maintain conversation context.
2. **Monitor `finish_reason`**: `"stop"` = natural end; `"length"` = truncated; `"tool_calls"` = model wants to call a function.
3. **System messages** are optional but recommended for controlling tone and behavior.
4. Hy3 supports **256K context**, so very long multi-turn conversations are possible.

---

## Run the Script

```bash
pip install openai
python 01-basic-chat.py
```
