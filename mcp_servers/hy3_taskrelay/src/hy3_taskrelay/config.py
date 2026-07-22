"""Environment-only configuration for the Hy3 API."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from urllib.parse import urlsplit

from pydantic import BaseModel, SecretStr


class ConfigError(ValueError):
    """Raised when a required TaskRelay setting is invalid or absent."""


_UNEXPANDED_VARIABLE = re.compile(r"^\$\{(?:env:)?([A-Z][A-Z0-9_]*)(?::-[^}]*)?\}$")


def _contains_control_characters(value: str) -> bool:
    return any(ord(character) < 32 or ord(character) == 127 for character in value)


def _is_printable_ascii_token(value: str) -> bool:
    return value.isascii() and all(33 <= ord(character) <= 126 for character in value)


class Settings(BaseModel):
    """Validated Hy3 settings read from the process environment."""

    api_key: SecretStr
    base_url: str
    model: str

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        values = os.environ if environ is None else environ
        api_key = values.get("HY3_API_KEY", "").strip()
        placeholder = _UNEXPANDED_VARIABLE.fullmatch(api_key)
        if not api_key or (placeholder and placeholder.group(1) == "HY3_API_KEY"):
            raise ConfigError("HY3_API_KEY is required to call a TaskRelay tool.")
        if not 8 <= len(api_key) <= 4_096 or not _is_printable_ascii_token(api_key):
            raise ConfigError(
                "HY3_API_KEY must be 8 to 4096 printable ASCII characters without whitespace."
            )
        base_url = values.get("HY3_BASE_URL", "").strip()
        if len(base_url) > 2_048 or _contains_control_characters(base_url):
            raise ConfigError("HY3_BASE_URL must be at most 2048 characters without control bytes.")
        try:
            parsed = urlsplit(base_url)
            _ = parsed.port
            hostname = parsed.hostname
        except ValueError:
            raise ConfigError("HY3_BASE_URL must be a valid URL with a valid port.") from None
        loopback_http = parsed.scheme == "http" and hostname in {"127.0.0.1", "localhost"}
        if parsed.scheme != "https" and not loopback_http:
            raise ConfigError(
                "HY3_BASE_URL must use https (http is allowed only for a loopback test server)."
            )
        if (
            not hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ConfigError(
                "HY3_BASE_URL must include a host and must not contain credentials, query, "
                "or fragment."
            )
        model = values.get("HY3_MODEL", "").strip()
        model_placeholder = _UNEXPANDED_VARIABLE.fullmatch(model)
        if not model or (model_placeholder and model_placeholder.group(1) == "HY3_MODEL"):
            raise ConfigError("HY3_MODEL must name the Hy3 model to call.")
        if len(model) > 256 or _contains_control_characters(model):
            raise ConfigError("HY3_MODEL must be at most 256 characters without control bytes.")
        return cls(
            api_key=SecretStr(api_key),
            base_url=base_url,
            model=model,
        )
