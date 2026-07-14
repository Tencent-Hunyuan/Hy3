"""Environment-based configuration for the MCP server."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values


class ConfigurationError(ValueError):
    """Raised when required server configuration is invalid or missing."""


_VALID_REASONING_EFFORTS = {"high", "low", "no_think"}


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings loaded exclusively from environment variables."""

    api_key: str
    base_url: str
    model: str = "hy3"
    reasoning_effort: str = "high"
    timeout: float = 120.0
    max_diff_chars: int = 120_000
    workspace_root: Path = Path.cwd()

    @classmethod
    def from_env(cls) -> Settings:
        """Load settings from the process environment and an optional dotenv file."""
        file_values = _load_env_file()

        def value(name: str, default: str = "") -> str:
            raw = os.environ.get(name)
            if raw is None:
                raw = file_values.get(name, default)
            return str(raw or default).strip()

        api_key = value("HY3_API_KEY")
        base_url = value("HY3_BASE_URL").rstrip("/")
        model = value("HY3_MODEL", "hy3")
        reasoning_effort = value("HY3_REASONING_EFFORT", "high")
        workspace = value("HY3_WORKSPACE_ROOT", str(Path.cwd()))

        if not api_key:
            raise ConfigurationError("HY3_API_KEY is required")
        if not base_url:
            raise ConfigurationError("HY3_BASE_URL is required")
        if not model:
            raise ConfigurationError("HY3_MODEL must not be empty")
        if reasoning_effort not in _VALID_REASONING_EFFORTS:
            allowed = ", ".join(sorted(_VALID_REASONING_EFFORTS))
            raise ConfigurationError(f"HY3_REASONING_EFFORT must be one of: {allowed}")

        timeout = _positive_float("HY3_TIMEOUT", 120.0, file_values)
        max_diff_chars = _positive_int("HY3_MAX_DIFF_CHARS", 120_000, file_values)
        workspace_root = Path(workspace).expanduser().resolve()
        if not workspace_root.is_dir():
            raise ConfigurationError(
                f"HY3_WORKSPACE_ROOT is not an existing directory: {workspace_root}"
            )

        return cls(
            api_key=api_key,
            base_url=base_url,
            model=model,
            reasoning_effort=reasoning_effort,
            timeout=timeout,
            max_diff_chars=max_diff_chars,
            workspace_root=workspace_root,
        )


def _load_env_file() -> Mapping[str, str | None]:
    raw_path = os.environ.get("HY3_ENV_FILE", "").strip()
    if not raw_path:
        return {}
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    path = path.resolve()
    if not path.is_file():
        raise ConfigurationError(f"HY3_ENV_FILE is not an existing file: {path}")
    return dotenv_values(path)


def _configured_value(
    name: str,
    default: str,
    file_values: Mapping[str, str | None],
) -> str:
    raw = os.environ.get(name)
    if raw is None:
        raw = file_values.get(name, default)
    return str(raw or default)


def _positive_float(
    name: str,
    default: float,
    file_values: Mapping[str, str | None],
) -> float:
    raw = _configured_value(name, str(default), file_values)
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be a number") from exc
    if value <= 0:
        raise ConfigurationError(f"{name} must be greater than zero")
    return value


def _positive_int(
    name: str,
    default: int,
    file_values: Mapping[str, str | None],
) -> int:
    raw = _configured_value(name, str(default), file_values)
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc
    if value <= 0:
        raise ConfigurationError(f"{name} must be greater than zero")
    return value
