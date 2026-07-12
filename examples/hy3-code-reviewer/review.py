"""Hy3 Code Reviewer — AI-powered code review powered by Tencent Hy3.

Usage::

    export HY3_BASE_URL=http://127.0.0.1:8000/v1
    export HY3_API_KEY=your-api-key
    python review.py path/to/file.py

Environment:
    HY3_BASE_URL  — Hy3 API endpoint (default: http://127.0.0.1:8000/v1)
    HY3_API_KEY   — API key (default: EMPTY for local deployments)
    HY3_MODEL     — Model name (default: tencent/Hy3)
"""

import os
import sys
from openai import OpenAI

BASE_URL = os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.environ.get("HY3_API_KEY", "EMPTY")
MODEL = os.environ.get("HY3_MODEL", "tencent/Hy3")

REVIEW_PROMPT = """You are a senior code reviewer. Analyze the following code and provide:

1. **Summary**: One-sentence overview of what the code does.
2. **Bugs**: Any bugs or potential issues (with line references).
3. **Style**: Style/readability suggestions.
4. **Security**: Security concerns (if any).
5. **Improvements**: Suggested improvements (performance, maintainability).

Be concise. Use bullet points. Reference specific lines where possible."""


def review_code(filepath: str) -> str:
    """Send code to Hy3 for review and return the response."""
    with open(filepath, "r", encoding="utf-8") as f:
        code = f.read()

    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

    # Truncate very large files
    max_chars = 30_000
    if len(code) > max_chars:
        code = code[:max_chars] + f"\n\n... (truncated {len(code) - max_chars:,d} chars)"

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": REVIEW_PROMPT},
            {"role": "user", "content": f"Review this code file ({filepath}):\n\n```\n{code}\n```"},
        ],
        temperature=0.3,
        max_tokens=2048,
    )

    return resp.choices[0].message.content or "(empty response)"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python review.py <filepath>")
        sys.exit(1)

    filepath = sys.argv[1]
    print(f"🔍 Hy3 Code Review: {filepath}\n")
    result = review_code(filepath)
    print(result)
