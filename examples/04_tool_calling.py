"""
04_tool_calling.py — Hy3 Tool Calling Example
==============================================
Demo: Single function call + Multi-turn tool loop + Forced tool invocation

Run:
    python 04_tool_calling.py

Prerequisites:
    Server must enable tool calling support:
    - vLLM: --tool-call-parser hy_v3 --enable-auto-tool-choice
    - SGLang: --tool-call-parser hunyuan

Environment Variables:
    HY3_BASE_URL  - API endpoint (default: http://127.0.0.1:8000/v1)
    HY3_API_KEY   - API key (default: EMPTY)
    HY3_MODEL     - Model name (default: hy3)
"""

import json
import os
from openai import OpenAI

# ── Configuration ────────────────────────────────────────
BASE_URL = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.getenv("HY3_API_KEY", "EMPTY")
MODEL = os.getenv("HY3_MODEL", "hy3")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)


# ── Simulated tool functions ─────────────────────────────
def get_weather(city: str) -> dict:
    """Simulated weather query API"""
    weather_db = {
        "Beijing": {"temp": 28, "condition": "Sunny", "humidity": 45},
        "Shanghai": {"temp": 32, "condition": "Cloudy", "humidity": 72},
        "Shenzhen": {"temp": 35, "condition": "Showers", "humidity": 85},
        "Guangzhou": {"temp": 33, "condition": "Thunderstorms", "humidity": 80},
    }
    return weather_db.get(city, {"temp": 25, "condition": "Sunny", "humidity": 50})


def calculate(expression: str) -> dict:
    """Simulated math calculator"""
    try:
        result = eval(expression)  # Demo only; use a safe parser in production
        return {"expression": expression, "result": result}
    except Exception as e:
        return {"expression": expression, "error": str(e)}


def search_docs(query: str) -> dict:
    """Simulated document search API"""
    docs = {
        "Hy3 parameters": "Hy3 is a 295B-parameter MoE model with 21B active parameters.",
        "MoE architecture": "Mixture of Experts reduces inference cost via sparse activation, activating only some experts each time.",
        "Context length": "Hy3 supports a context length of 256K tokens.",
    }
    for key, value in docs.items():
        if key in query:
            return {"query": query, "result": value}
    return {"query": query, "result": "No relevant documents found."}


# Tool routing table
TOOL_HANDLERS = {
    "get_weather": get_weather,
    "calculate": calculate,
    "search_docs": search_docs,
}


# ── Tool definitions (OpenAI format) ─────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Query real-time weather for a city, including temperature, condition, and humidity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name, e.g., Beijing, Shanghai, Shenzhen",
                    }
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Evaluate a math expression and return the result.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Math expression, e.g., (2 + 3) * 4",
                    }
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_docs",
            "description": "Search the knowledge base for documents related to the query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query keywords",
                    }
                },
                "required": ["query"],
            },
        },
    },
]


# ══════════════════════════════════════════════════════
# Example 1: Single tool call
# ══════════════════════════════════════════════════════
def single_tool_call():
    """Model decides to call a tool once, then returns the final answer"""
    print("=" * 60)
    print("Example 1: Single Tool Call")
    print("=" * 60)

    messages = [
        {"role": "user", "content": "What's the weather like in Beijing today?"}
    ]

    print(f"\n[User]: {messages[0]['content']}")

    # Round 1: Model decides to call a tool
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
        temperature=0.9,
    )

    message = response.choices[0].message

    if message.tool_calls:
        for tool_call in message.tool_calls:
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments)
            print(f"\n[Tool Call] {func_name}({json.dumps(func_args, ensure_ascii=False)})")

            # Execute tool
            handler = TOOL_HANDLERS.get(func_name)
            if handler:
                result = handler(**func_args)
            else:
                result = {"error": f"Unknown tool: {func_name}"}

            print(f"[Tool Result] {json.dumps(result, ensure_ascii=False)}")

            # Add tool call and result to conversation history
            messages.append(message)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, ensure_ascii=False),
            })

        # Round 2: Model generates final answer based on tool results
        final_response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.9,
        )

        print(f"\n[Assistant]: {final_response.choices[0].message.content}")
        return final_response
    else:
        print(f"\n[Assistant]: {message.content}")
        return response


# ══════════════════════════════════════════════════════
# Example 2: Multi-turn tool loop
# ══════════════════════════════════════════════════════
def multi_turn_tool_loop():
    """Model may call multiple tools consecutively, forming a tool loop"""
    print("\n" + "=" * 60)
    print("Example 2: Multi-turn Tool Loop")
    print("=" * 60)

    messages = [
        {
            "role": "system",
            "content": (
                "You are an assistant with access to weather, calculator, "
                "and doc search tools. Call tools sequentially if you need "
                "multiple pieces of information."
            ),
        },
        {
            "role": "user",
            "content": "Check the weather in Beijing and Shanghai, then calculate the temperature difference between the two cities.",
        },
    ]

    print(f"\n[User]: {messages[-1]['content']}")

    max_iterations = 5  # Prevent infinite loop

    for iteration in range(max_iterations):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.9,
        )

        message = response.choices[0].message

        # If no tool calls, the model has given the final answer
        if not message.tool_calls:
            print(f"\n[Assistant]: {message.content}")
            break

        # Process all tool calls
        messages.append(message)
        for tool_call in message.tool_calls:
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments)
            print(f"\n[Iteration {iteration + 1}] "
                  f"Tool Call: {func_name}({json.dumps(func_args, ensure_ascii=False)})")

            handler = TOOL_HANDLERS.get(func_name)
            if handler:
                result = handler(**func_args)
            else:
                result = {"error": f"Unknown tool: {func_name}"}

            print(f"[Iteration {iteration + 1}] "
                  f"Tool Result: {json.dumps(result, ensure_ascii=False)}")

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, ensure_ascii=False),
            })
    else:
        print(f"\n[Warning] Max iterations ({max_iterations}) reached, forcing stop.")

    return messages


# ══════════════════════════════════════════════════════
# Example 3: Force a specific tool
# ══════════════════════════════════════════════════════
def forced_tool_call():
    """Force the model to use a specific tool via tool_choice"""
    print("\n" + "=" * 60)
    print("Example 3: Forced Tool Call")
    print("=" * 60)

    messages = [
        {"role": "user", "content": "Calculate (15 + 27) * 3 - 18"}
    ]

    print(f"\n[User]: {messages[0]['content']}")

    # Force use of the calculate tool
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS,
        tool_choice={"type": "function", "function": {"name": "calculate"}},
        temperature=0.9,
    )

    message = response.choices[0].message

    if message.tool_calls:
        tool_call = message.tool_calls[0]
        func_args = json.loads(tool_call.function.arguments)
        print(f"\n[Forced Tool Call] calculate({json.dumps(func_args, ensure_ascii=False)})")

        result = calculate(**func_args)
        print(f"[Tool Result] {json.dumps(result, ensure_ascii=False)}")

        messages.append(message)
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(result, ensure_ascii=False),
        })

        final_response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.9,
        )
        print(f"\n[Assistant]: {final_response.choices[0].message.content}")
    else:
        print(f"\n[Assistant]: {message.content}")

    return response


# ── Main entry ───────────────────────────────────────────
if __name__ == "__main__":
    print("Hy3 Tool Calling Example")
    print(f"API: {BASE_URL} | Model: {MODEL}")
    print("Note: Server must enable --tool-call-parser and --enable-auto-tool-choice\n")

    single_tool_call()
    multi_turn_tool_loop()
    forced_tool_call()

    print("\n" + "=" * 60)
    print("All tool calling examples completed!")
    print("=" * 60)
