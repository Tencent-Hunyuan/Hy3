#!/usr/bin/env python3
"""最小 OpenRouter × Hy3 调用。优先读本目录 .env，否则读上级统一 .env。"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

here = Path(__file__).resolve().parent
load_dotenv(here / ".env")
load_dotenv(here.parent / ".env")

client = OpenAI(
    api_key=os.environ["OPENROUTER_API_KEY"],
    base_url=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
)
resp = client.chat.completions.create(
    model=os.environ.get("OPENROUTER_MODEL", "tencent/hy3"),
    messages=[{"role": "user", "content": "用一句话介绍 Hy3。"}],
)
print(resp.choices[0].message.content)
