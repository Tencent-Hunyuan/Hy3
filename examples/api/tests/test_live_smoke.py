"""Optional live TokenHub smoke test; disabled unless explicitly requested."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

from dotenv import load_dotenv

API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))
load_dotenv(API_DIR / ".env")

from common import create_client, load_config  # noqa: E402


@unittest.skipUnless(
    os.getenv("HY3_RUN_LIVE_TESTS") == "1" and os.getenv("HY3_API_KEY"),
    "set HY3_RUN_LIVE_TESTS=1 and HY3_API_KEY to run the live smoke test",
)
class LiveSmokeTest(unittest.TestCase):
    def test_minimal_chat_completion(self) -> None:
        config = load_config()
        client = create_client(config, timeout=60.0)
        response = client.chat.completions.create(
            model=config.model,
            messages=[{"role": "user", "content": "只回复 OK"}],
            temperature=0.0,
            max_tokens=16,
            extra_body={"thinking": {"type": "disabled"}},
        )
        self.assertTrue(response.choices)
        self.assertTrue(response.choices[0].message.content)


if __name__ == "__main__":
    unittest.main()
