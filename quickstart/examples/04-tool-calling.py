"""
Example 4: Tool Calling — function calling with single and multi-turn tool loops.

Usage:
    python 04-tool-calling.py

Prerequisites:
    - Hy3 server running at http://127.0.0.1:8000 (vLLM or SGLang)
    - vLLM must be launched with --tool-call-parser hy_v3 --enable-auto-tool-choice
      or SGLang with --tool-call-parser hunyuan
    - pip install openai
"""

import json
from openai import OpenAI

# ──────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────
BASE_URL = "http://127.0.0.1:8000/v1"
API_KEY = "EMPTY"
MODEL = "hy3"

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

# ──────────────────────────────────────────────────────────────────────
# Tool Definitions
# ──────────────────────────────────────────────────────────────────────
TOOLS = [
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
            "description": "Search the web for up-to-date information. Returns a list of relevant results.",
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


# ──────────────────────────────────────────────────────────────────────
# Mock Tool Executor (replace with real API calls in production)
# ──────────────────────────────────────────────────────────────────────
def execute_tool(name: str, arguments: dict) -> str:
    """Execute a tool and return the result as a JSON string."""
    if name == "get_weather":
        location = arguments.get("location", "unknown")
        # Simulated weather data
        weather_db = {
            "tokyo": (22, "partly cloudy", "65%"),
            "beijing": (30, "sunny", "40%"),
            "shanghai": (28, "light rain", "75%"),
            "guangzhou": (33, "thunderstorm", "85%"),
            "london": (18, "overcast", "70%"),
            "new york": (25, "clear", "55%"),
        }
        key = location.split(",")[0].strip().lower()
        temp, conditions, humidity = weather_db.get(key, (20, "unknown", "50%"))
        return json.dumps({
            "location": location,
            "temperature": temp,
            "conditions": conditions,
            "humidity": humidity,
            "unit": arguments.get("unit", "celsius"),
        })

    elif name == "search_web":
        query = arguments.get("query", "")
        num = min(arguments.get("num_results", 5), 10)
        return json.dumps({
            "query": query,
            "results": [
                {"title": f"Result {i} for '{query}'", "url": f"https://example.com/{i}", "snippet": f"Relevant information about {query}..."}
                for i in range(1, num + 1)
            ],
        })

    return json.dumps({"error": f"Unknown tool: {name}"})


# ──────────────────────────────────────────────────────────────────────
# 1. Single Tool Call
# ──────────────────────────────────────────────────────────────────────
def single_tool_call():
    print("=" * 60)
    print("1. SINGLE TOOL CALL")
    print("=" * 60)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "What's the weather in Tokyo?"}],
        tools=TOOLS,
        tool_choice="auto",
        temperature=0.9,
        top_p=1.0,
    )

    message = response.choices[0].message

    if message.tool_calls:
        for tc in message.tool_calls:
            print(f"\n🔧 Function called: {tc.function.name}")
            print(f"   Arguments:      {tc.function.arguments}")
            print(f"   Tool call ID:   {tc.id}")
            print(f"   Finish reason:  {response.choices[0].finish_reason}")
    else:
        print(f"\n💬 Direct response (no tool call):\n{message.content}")


# ──────────────────────────────────────────────────────────────────────
# 2. Multi-Turn Tool Loop (Agentic Pattern)
# ──────────────────────────────────────────────────────────────────────
def run_agent(user_query: str, max_turns: int = 5, verbose: bool = True):
    """
    Run the agent loop: call tools until the model gives a final answer.

    Args:
        user_query: The user's question or command.
        max_turns: Maximum number of tool-calling rounds before giving up.
        verbose: Print each step.

    Returns:
        The final answer string, or None if max_turns exceeded.
    """
    messages = [{"role": "user", "content": user_query}]

    for turn in range(max_turns):
        if verbose:
            print(f"\n--- Turn {turn + 1} ---")

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.9,
            top_p=1.0,
        )

        message = response.choices[0].message

        # Final answer — no more tool calls needed
        if not message.tool_calls:
            if verbose:
                print(f"✅ Final answer:\n{message.content}")
            return message.content

        # Add assistant message with tool calls to history
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

        # Execute each tool call and append results
        for tc in message.tool_calls:
            func_name = tc.function.name
            func_args = json.loads(tc.function.arguments)

            if verbose:
                print(f"🔧 Calling: {func_name}({json.dumps(func_args)})")

            result = execute_tool(func_name, func_args)

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

            if verbose:
                print(f"📥 Result: {result[:120]}{'...' if len(result) > 120 else ''}")

    print("⚠️ Max turns reached without final answer.")
    return None


def multi_turn_example():
    print("\n" + "=" * 60)
    print("2. MULTI-TURN TOOL LOOP")
    print("=" * 60)

    run_agent("What's the weather in Tokyo and Shanghai? Which city is warmer?")


# ──────────────────────────────────────────────────────────────────────
# 3. Parallel Tool Calls
# ──────────────────────────────────────────────────────────────────────
def parallel_tool_calls():
    print("\n" + "=" * 60)
    print("3. PARALLEL TOOL CALLS")
    print("=" * 60)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": "Compare the weather in Beijing, Shanghai, and Guangzhou."},
        ],
        tools=TOOLS,
        tool_choice="auto",
        temperature=0.9,
        top_p=1.0,
    )

    message = response.choices[0].message

    if message.tool_calls:
        print(f"\nModel requested {len(message.tool_calls)} parallel tool calls:\n")
        for i, tc in enumerate(message.tool_calls, 1):
            args = json.loads(tc.function.arguments)
            print(f"  {i}. {tc.function.name}({json.dumps(args)})")
        print("\n💡 Execute independent calls in parallel to minimize latency.")
    else:
        print(f"\nDirect response: {message.content}")


# ──────────────────────────────────────────────────────────────────────
# 4. Tool Choice Modes
# ──────────────────────────────────────────────────────────────────────
def tool_choice_modes():
    print("\n" + "=" * 60)
    print("4. TOOL CHOICE MODES")
    print("=" * 60)

    test_cases = [
        ("auto (no tool needed)", "auto", "Say hello in Chinese."),
        ("required (force tool)", "required", "Say hello in Chinese."),
        ("none (no tools)", "none", "What's the weather in Beijing?"),
    ]

    for label, tool_choice, prompt in test_cases:
        print(f"\n--- {label} ---")
        print(f"Prompt: {prompt}")

        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                tools=TOOLS,
                tool_choice=tool_choice if tool_choice != "required" else "required",
                temperature=0.9,
                top_p=1.0,
            )

            msg = response.choices[0].message
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    print(f"  → Tool: {tc.function.name}({tc.function.arguments})")
            else:
                print(f"  → Content: {msg.content[:100]}...")
        except Exception as e:
            print(f"  → Error: {e}")


# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    single_tool_call()
    multi_turn_example()
    parallel_tool_calls()
    tool_choice_modes()
