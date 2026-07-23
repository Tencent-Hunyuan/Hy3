"""Environment-backed configuration for the MCP server."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded lazily so MCP client env values take effect."""

    api_base: str
    api_key: str
    model: str
    data_dir: Path
    max_file_bytes: int
    timeout_seconds: float

    @classmethod
    def from_env(cls) -> Settings:
        data_dir = Path(os.environ.get("HY3_DATA_DIR", ".")).expanduser().resolve()
        return cls(
            api_base=os.environ.get("HY3_API_BASE", "http://127.0.0.1:8000/v1"),
            api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
            model=os.environ.get("HY3_MODEL", "hy3"),
            data_dir=data_dir,
            max_file_bytes=_positive_int("HY3_MAX_FILE_BYTES", 10 * 1024 * 1024),
            timeout_seconds=_positive_float("HY3_TIMEOUT_SECONDS", 120.0),
        )


def _positive_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


def _positive_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value
