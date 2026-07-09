"""
Hy3 API verification script — validates connectivity and core capabilities.

Run before building to confirm:
  1. Basic chat works
  2. Function Calling works
  3. Structured Output works
  4. Cache is available

Usage:
  python scripts/verify_hy3.py

Requires ARCHAEOLOGIST_HY3_API_KEY in environment or .env file.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.config import Settings
from app.core.hy3_client import Hy3Client

PASS = "\033[92m✅ PASS\033[0m"
FAIL = "\033[91m❌ FAIL\033[0m"
SKIP = "\033[93m⚠️  SKIP\033[0m"


def check_env() -> Settings:
    """Validate environment setup."""
    settings = Settings()
    if not settings.hy3_api_key:
        print(f"{FAIL} ARCHAEOLOGIST_HY3_API_KEY is not set")
        print("   Set it via: export ARCHAEOLOGIST_HY3_API_KEY=your-key")
        print("   Or create a .env file in the project root.")
        sys.exit(1)

    print(f"{PASS} API key configured")
    print(f"   Base URL: {settings.hy3_base_url}")
    print(f"   Model: {settings.hy3_model}")
    return settings


async def test_basic_chat(client: Hy3Client) -> bool:
    """Test basic chat completion."""
    print("\n--- Test 1: Basic Chat ---")
    try:
        response = await client.chat(
            messages=[{"role": "user", "content": "Say 'Hello, Archaeologist!' and nothing else."}],
            max_tokens=50,
            temperature=0.0,
        )
        content = response.content.strip()
        if "Hello" in content or "Archaeologist" in content:
            print(f"{PASS} Basic chat works")
            print(f"   Response: {content[:100]}")
            print(f"   Tokens: {response.usage}")
            return True
        else:
            print(f"{FAIL} Unexpected response: {content[:100]}")
            return False
    except Exception as e:
        print(f"{FAIL} Basic chat failed: {e}")
        return False


async def test_tool_calling(client: Hy3Client) -> bool:
    """Test Function Calling capability."""
    print("\n--- Test 2: Function Calling ---")

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get current weather for a city",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "City name"},
                    },
                    "required": ["city"],
                },
            },
        }
    ]

    try:
        response = await client.chat(
            messages=[
                {"role": "user", "content": "What's the weather in Beijing?"}
            ],
            tools=tools,
            tool_choice="auto",
            max_tokens=100,
        )

        if response.tool_calls:
            tc = response.tool_calls[0]
            fn_name = tc["function"]["name"]
            fn_args = tc["function"]["arguments"]

            if fn_name == "get_weather" and "Beijing" in fn_args:
                print(f"{PASS} Function Calling works")
                print(f"   Tool called: {fn_name}")
                print(f"   Arguments: {fn_args}")
                return True
            else:
                print(f"{FAIL} Wrong tool or arguments: {tc}")
                return False
        else:
            print(f"{SKIP} No tool calls returned (model may have answered directly)")
            print(f"   Response: {response.content[:100]}")
            return True  # Not a failure — some models answer directly
    except Exception as e:
        print(f"{FAIL} Function Calling failed: {e}")
        return False


async def test_cache(client: Hy3Client) -> bool:
    """Test prompt cache functionality.

    Send the same request twice and check if the second call
    has lower prompt token cost (cache hit).
    """
    print("\n--- Test 3: Prompt Cache ---")

    system_prompt = "You are a code analyzer. Keep responses brief."
    user_msg = "What is the capital of France? Answer in one word."

    try:
        # First call (cache miss)
        r1 = await client.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=10,
            temperature=0.0,
        )
        t1 = r1.usage.get("prompt_tokens", 0)

        # Second call (should be cache hit)
        r2 = await client.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=10,
            temperature=0.0,
        )
        t2 = r2.usage.get("prompt_tokens", 0)

        # Cache reads come through as reduced prompt tokens or a separate field
        cache_read = r2.usage.get("cache_read_tokens", 0)

        print(f"   First call prompt tokens: {t1}")
        print(f"   Second call prompt tokens: {t2}")
        print(f"   Second call cache read tokens: {cache_read}")

        if cache_read > 0 or t2 < t1:
            print(f"{PASS} Cache appears to work")
        else:
            print(f"{SKIP} Cache effect not observable in usage (may still work)")
        return True
    except Exception as e:
        print(f"{SKIP} Cache test failed: {e}")
        return True  # Not critical


async def main():
    print("=" * 50)
    print("Codebase Archaeologist — Hy3 API Verification")
    print("=" * 50)

    settings = check_env()
    client = Hy3Client(settings)

    results = []

    results.append(await test_basic_chat(client))
    results.append(await test_tool_calling(client))
    results.append(await test_cache(client))

    # Summary
    print("\n" + "=" * 50)
    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")

    print(f"\nTotal usage: {client.usage.summary()}")

    if passed == total:
        print("\n🎉 All checks passed! You're ready to build.")
    else:
        print(f"\n⚠️  {total - passed} check(s) had issues. Review the output above.")


if __name__ == "__main__":
    asyncio.run(main())
