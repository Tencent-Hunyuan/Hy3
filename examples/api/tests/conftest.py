"""Make the adjacent example helper importable during repository-root tests."""

from __future__ import annotations

import sys
from pathlib import Path

API_EXAMPLES = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_EXAMPLES))
