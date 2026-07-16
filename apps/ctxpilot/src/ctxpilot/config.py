"""Configuration: read Hy3 credentials from env / local .env only.

Safety (see DESIGN.md §8 S5): the API key is never written anywhere except the
user's local .env, is never transmitted by the app to anyone but the configured
Hy3 endpoint, and is never logged.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DEFAULT_BASE_URL = "https://tokenhub.tencentmaas.com/v1"  # Hy3 cloud (TokenHub); local vLLM overrides this
DEFAULT_MODEL = "hy3"
DEFAULT_REASONING = "low"

# Local, user-private config store (NOT the project .env, so we never clobber it).
_CONFIG_DIR = Path.home() / ".ctxpilot"
_CONFIG_FILE = _CONFIG_DIR / "config.json"


@dataclass
class Config:
    hy3_api_key: str = ""
    hy3_base_url: str = DEFAULT_BASE_URL
    hy3_model: str = DEFAULT_MODEL
    hy3_reasoning_effort: str = DEFAULT_REASONING
    project_path: Path = field(default_factory=Path.cwd)
    # Agents to scan. Empty list => auto-discover all registered adapters.
    agents: list[str] = field(default_factory=list)
    # Project roots the dashboard auto-scans. Empty => [project_path].
    project_roots: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.project_path, Path):
            self.project_path = Path(self.project_path)

    @classmethod
    def from_env(cls, project_path: str | os.PathLike | None = None) -> "Config":
        return cls(
            hy3_api_key=os.getenv("HY3_API_KEY", ""),
            hy3_base_url=os.getenv("HY3_BASE_URL", DEFAULT_BASE_URL),
            hy3_model=os.getenv("HY3_MODEL", DEFAULT_MODEL),
            hy3_reasoning_effort=os.getenv("HY3_REASONING_EFFORT", DEFAULT_REASONING),
            project_path=Path(project_path) if project_path else Path.cwd(),
        )

    @classmethod
    def from_store(cls, project_path: str | os.PathLike | None = None) -> "Config":
        """Env first, then overlay the local on-disk store (set via the UI)."""
        c = cls.from_env(project_path)
        if _CONFIG_FILE.exists():
            try:
                data = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
            except Exception:
                data = {}
            c.hy3_api_key = data.get("hy3_api_key", c.hy3_api_key)
            c.hy3_base_url = data.get("hy3_base_url", c.hy3_base_url)
            c.hy3_model = data.get("hy3_model", c.hy3_model)
            c.hy3_reasoning_effort = data.get("hy3_reasoning_effort", c.hy3_reasoning_effort)
            c.project_roots = data.get("project_roots", c.project_roots)
        return c

    def save(self) -> None:
        """Persist to the private local store (mode 600 on POSIX)."""
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "hy3_api_key": self.hy3_api_key,
            "hy3_base_url": self.hy3_base_url,
            "hy3_model": self.hy3_model,
            "hy3_reasoning_effort": self.hy3_reasoning_effort,
            "project_roots": list(self.project_roots),
        }
        _CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            os.chmod(str(_CONFIG_FILE), 0o600)
        except OSError:
            pass

    @property
    def has_credentials(self) -> bool:
        return bool(self.hy3_api_key and self.hy3_base_url)
