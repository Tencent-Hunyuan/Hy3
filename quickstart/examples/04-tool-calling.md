# Example 4: Tool Calling

Use Hy3's function-calling capability to build agentic workflows — let the model decide when and how to call external tools.

## What You'll Learn

- Define tools with JSON Schema
- Make a single tool call and parse the response
- Implement a multi-turn tool loop (execute → feed result → continue)
- Handle parallel tool calls

---

## Tool Definition

Tools are defined using the OpenAI function-calling format. Here are two example tools:

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a city. Returns temperature, conditions, and humidity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name and optional country code, e.g. 'Beijing, CN'",
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "Temperature unit. Default: celsius.",
                    },
                },
                "required": ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web for up-to-date information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query.",
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "Number of results to return (1-10). Default: 5.",
                        "minimum": 1,
                        "maximum": 10,
                    },
                },
                "required": ["query"],
            },
        },
    },
]
```

---

## Single Tool Call

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
        {"role": "user", "content": "What's the weather in Tokyo?"},
    ],
    tools=tools,
    tool_choice="auto",  # Let the model decide
    temperature=0.9,
    top_p=1.0,
)
```

### Response Parsing

```python
message = response.choices[0].message

# Check if the model wants to call a tool
if message.tool_calls:
    for tool_call in message.tool_calls:
        print(f"Function called: {tool_call.function.name}")
        print(f"Arguments: {tool_call.function.arguments}")
        print(f"Tool call ID: {tool_call.id}")
elif message.content:
    print(f"Direct response: {message.content}")
```

### Sample Response

```json
{
  "id": "chatcmpl-xyz789",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": null,
        "tool_calls": [
          {
            "id": "call_abc123",
            "type": "function",
            "function": {
              "name": "get_weather",
              "arguments": "{\"location\": \"Tokyo, JP\", \"unit\": \"celsius\"}"
            }
          }
        ]
      },
      "finish_reason": "tool_calls"
    }
  ],
  "usage": {
    "prompt_tokens": 120,
    "completion_tokens": 25,
    "total_tokens": 145
  }
}
```

### Sample Output

```
Function called: get_weather
Arguments: {"location": "Tokyo, JP", "unit": "celsius"}
Tool call ID: call_abc123
```

---

## Multi-Turn Tool Loop

The canonical agentic pattern: call → execute → feed result → iterate.

```python
import json

def execute_tool(name: str, arguments: dict) -> str:
    """Mock tool executor — replace with real API calls."""
    if name == "get_weather":
        location = arguments.get("location", "unknown")
        return json.dumps({
            "location": location,
            "temperature": 22,
            "conditions": "partly cloudy",
            "humidity": "65%",
            "unit": arguments.get("unit", "celsius"),
        })
    elif name == "search_web":
        query = arguments.get("query", "")
        return json.dumps({
            "query": query,
            "results": [
                {"title": f"Result 1 for '{query}'", "snippet": "..."},
                {"title": f"Result 2 for '{query}'", "snippet": "..."},
            ],
        })
    return json.dumps({"error": f"Unknown tool: {name}"})


def run_agent(user_query: str, max_turns: int = 5):
    """Run the agent loop: call tools until the model gives a final answer."""
    messages = [{"role": "user", "content": user_query}]

    for turn in range(max_turns):
        print(f"\n--- Turn {turn + 1} ---")

        response = client.chat.completions.create(
            model="hy3",
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.9,
            top_p=1.0,
        )

        message = response.choices[0].message

        # Final answer — no tool calls
        if not message.tool_calls:
            print(f"✅ Final answer:\n{message.content}")
            return message.content

        # Execute tool calls
        messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in message.tool_calls
            ],
        })

        for tc in message.tool_calls:
            func_name = tc.function.name
            func_args = json.loads(tc.function.arguments)
            print(f"🔧 Calling: {func_name}({func_args})")

            result = execute_tool(func_name, func_args)

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })
            print(f"📥 Result: {result[:100]}...")

    print("⚠️ Max turns reached without final answer.")
    return None


# Run the agent
run_agent("What's the weather in Tokyo and search for best ramen shops there?")
```

### Sample Output

```
--- Turn 1 ---
🔧 Calling: get_weather({'location': 'Tokyo, JP', 'unit': 'celsius'})
📥 Result: {"location": "Tokyo, JP", "temperature": 22, "conditions": "partly cloudy", "humidity": "65%", "unit": "celsius"}

🔧 Calling: search_web({'query': 'best ramen shops Tokyo 2025'})
📥 Result: {"query": "best ramen shops Tokyo 2025", "results": [...]}

--- Turn 2 ---
✅ Final answer:
Here's what I found for Tokyo:

🌤️ **Weather**: Currently 22°C, partly cloudy with 65% humidity.

🍜 **Top Ramen Shops** (from web search):
1. Ichiran Shibuya — Famous for solo booth dining and tonkotsu ramen
2. Nakiryu — Michelin-starred tantanmen
3. Fuunji — Known for tsukemen (dipping ramen)
4. Afuri — Yuzu-infused light broth, very refreshing for this weather

Given the mild weather, it's a perfect day to explore these spots on foot!
```

---

## Parallel Tool Calls

Hy3 can call multiple tools simultaneously when they're independent:

```python
response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "Compare the weather in Beijing, Shanghai, and Guangzhou."},
    ],
    tools=tools,
    tool_choice="auto",
)

for tc in response.choices[0].message.tool_calls:
    print(f"→ {tc.function.name}({tc.function.arguments})")
```

### Sample Output (Parallel)

```
→ get_weather({"location": "Beijing, CN"})
→ get_weather({"location": "Shanghai, CN"})
→ get_weather({"location": "Guangzhou, CN"})
```

> 💡 **Tip**: Execute independent tool calls **in parallel** (e.g., with `asyncio.gather` or `concurrent.futures`) to minimize latency.

---

## Key Takeaways

1. **Define tools** with clear names, descriptions, and JSON Schema parameters — the model uses these to decide when and how to call.
2. **`tool_choice: "auto"`** lets the model decide; use `"required"` to force a tool call.
3. **Always append the tool result** to `messages` with `role: "tool"` and the matching `tool_call_id`.
4. **Loop until `finish_reason != "tool_calls"`** or the model returns a `content` response.
5. **Execute independent calls in parallel** to minimize total latency.
6. **Hy3's tool-calling stability** has been specifically optimized — expect production-grade reliability.

---

## Run the Script

```bash
pip install openai
python 04-tool-calling.py
```
