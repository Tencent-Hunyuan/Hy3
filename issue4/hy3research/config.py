"""Configuration loader: reads .env from project root or cwd, falls back to env vars."""

from __future__ import annotations

import os
from pathlib import Path


def _find_dotenv() -> Path | None:
    """Search for .env file: project root first, then cwd, then parent dirs."""
    candidates = [
        Path(__file__).resolve().parent.parent / ".env",  # project root
        Path.cwd() / ".env",
    ]
    # also search up from cwd
    p = Path.cwd()
    while p != p.parent:
        candidates.append(p / ".env")
        p = p.parent
    for path in candidates:
        if path.is_file():
            return path
    return None


def _load_dotenv() -> None:
    """Load .env file into os.environ (does not override existing vars)."""
    env_path = _find_dotenv()
    if env_path is None:
        return
    try:
        text = env_path.read_text(encoding="utf-8-sig")
    except OSError:
        return
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, val = line.partition("=")
        name = name.strip()
        val = val.strip().strip('"').strip("'")
        if name and name not in os.environ:
            os.environ[name] = val


class _Config:
    """Namespace for configuration values, loaded from env with defaults."""

    def _get(self, key: str, default: str = "") -> str:
        return os.environ.get(key, default).strip()

    @property
    def HY3_API_KEY(self) -> str:
        return self._get("HY3_API_KEY")

    @property
    def HY3_BASE_URL(self) -> str:
        return self._get("HY3_BASE_URL", "https://api.hunyuan.cloud.tencent.com/v1")

    @property
    def HY3_MODEL(self) -> str:
        return self._get("HY3_MODEL", "hunyuan-3.0-free")

    @property
    def HY3_MAX_TOKENS(self) -> int:
        val = self._get("HY3_MAX_TOKENS", "16384")
        try:
            return int(val)
        except ValueError:
            return 16384

    @property
    def TAVILY_API_KEY(self) -> str:
        return self._get("TAVILY_API_KEY")

    @property
    def HY3_RESEARCH_PORT(self) -> int:
        val = self._get("HY3_RESEARCH_PORT", "8899")
        try:
            return int(val)
        except ValueError:
            return 8899

    @property
    def is_mock(self) -> bool:
        return not self.HY3_API_KEY


# Load on import
_load_dotenv()
Config = _Config()
