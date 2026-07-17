"""Pytest setup for offline and opt-in live tests."""

from __future__ import annotations

import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


def pytest_configure(config: object) -> None:
    config.addinivalue_line(  # type: ignore[attr-defined]
        "markers", "live: requires an explicitly configured HY3_API_KEY"
    )
