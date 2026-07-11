"""
Demo: call the review_diff tool via MCP client.

Prerequisites:
  1. Start the Hy3 vLLM server (see README).
  2. Install: pip install mcp hy3-code-review-mcp
  3. Run: python demo_review_diff.py
"""

import asyncio
import os

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SAMPLE_DIFF = """\
diff --git a/auth/login.py b/auth/login.py
index e3b1c2d..7f9a2b1 100644
--- a/auth/login.py
+++ b/auth/login.py
@@ -12,7 +12,7 @@ def authenticate(username: str, password: str) -> bool:
     query = f"SELECT * FROM users WHERE username = '{username}'"
     cursor.execute(query)
     user = cursor.fetchone()
-    if user and user['password'] == password:
+    if user and user['password'] == hashlib.md5(password.encode()).hexdigest():
         return True
     return False
"""


async def main():
    server_params = StdioServerParameters(
        command="uvx",
        args=["hy3-code-review-mcp"],
        env={
            "HY3_BASE_URL": os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
            "HY3_API_KEY": os.environ.get("HY3_API_KEY", "EMPTY"),
            "HY3_MODEL": os.environ.get("HY3_MODEL", "hy3"),
        },
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("Available tools:", [t.name for t in tools.tools])

            result = await session.call_tool(
                "review_diff",
                arguments={
                    "diff": SAMPLE_DIFF,
                    "context": "Upgrading password comparison to use MD5 hash",
                    "reasoning_effort": "high",
                },
            )

            print("\n=== Hy3 Code Review ===\n")
            for content in result.content:
                print(content.text)


if __name__ == "__main__":
    asyncio.run(main())
