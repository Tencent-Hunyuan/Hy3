from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    api_base: str
    api_key: str | None
    model: str
    reasoning_effort: str
    offline: bool
    timeout_seconds: float
    root: Path

    @property
    def api_key_present(self) -> bool:
        return bool(self.api_key)


def load_settings() -> Settings:
    api_key = os.getenv("HY3_API_KEY")
    offline_raw = os.getenv("HY3_OFFLINE", "").lower()
    offline = offline_raw in {"1", "true", "yes"} or not api_key
    root = Path(os.getenv("HY3_LEADINTEL_ROOT", Path.cwd())).expanduser().resolve()
    return Settings(
        api_base=os.getenv("HY3_API_BASE", "http://127.0.0.1:8000/v1").rstrip("/"),
        api_key=api_key,
        model=os.getenv("HY3_MODEL", "hy3"),
        reasoning_effort=os.getenv("HY3_REASONING_EFFORT", "high"),
        offline=offline,
        timeout_seconds=float(os.getenv("HY3_TIMEOUT_SECONDS", "60")),
        root=root,
    )
