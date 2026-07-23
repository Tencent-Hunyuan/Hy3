"""Runtime configuration with safe defaults for local Hy3 deployments."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Settings:
    base_url: str
    api_key: str
    model: str
    timeout_seconds: float
    demo_mode: bool

    @classmethod
    def from_env(cls) -> Settings:
        raw_timeout = os.getenv("HY3_TIMEOUT_SECONDS", "120")
        try:
            timeout = float(raw_timeout)
        except ValueError as error:
            raise ValueError("HY3_TIMEOUT_SECONDS must be a number") from error

        settings = cls(
            base_url=os.getenv(
                "HY3_BASE_URL", "https://tokenhub-intl.tencentcloudmaas.com/v1"
            ).rstrip("/"),
            api_key=os.getenv("HY3_API_KEY", ""),
            model=os.getenv("HY3_MODEL", "hy3"),
            timeout_seconds=timeout,
            demo_mode=os.getenv("SCENARIOFORGE_DEMO_MODE", "").lower()
            in {"1", "true", "yes"},
        )
        settings.validate()
        return settings

    @property
    def live_ready(self) -> bool:
        return bool(self.api_key)

    def validate(self) -> None:
        parsed = urlsplit(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("HY3_BASE_URL must be an absolute HTTP(S) URL")
        if parsed.username or parsed.password:
            raise ValueError("HY3_BASE_URL must not contain credentials")
        if not self.model.strip():
            raise ValueError("HY3_MODEL must not be empty")
        if self.timeout_seconds <= 0:
            raise ValueError("HY3_TIMEOUT_SECONDS must be greater than zero")
