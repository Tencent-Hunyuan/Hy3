#!/usr/bin/env python3
"""最小 OpenRouter × Hy3 调用。先 cp .env.example .env 并填写 Key。"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).resolve().parent / ".env")

client = OpenAI(
    api_key=os.environ["OPENROUTER_API_KEY"],
    base_url=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
)
resp = client.chat.completions.create(
    model=os.environ.get("OPENROUTER_MODEL", "tencent/hy3"),
    messages=[{"role": "user", "content": "用一句话介绍 Hy3。"}],
)
print(resp.choices[0].message.content)
