# Copyright (C) 2026 Tencent. Licensed under the Apache License, Version 2.0.
# SPDX-License-Identifier: Apache-2.0
"""Runtime settings — backend selection is driven purely by environment variables.

Backend selection rule (documented in README §配置):

* ``HYSHELL_OFFLINE=1``            → **FAKE** (forced offline, even if a key is set)
* elif ``HY3_API_KEY`` is set      → **REAL**: ``base_url = HY3_API_BASE``
  (default ``http://127.0.0.1:8000/v1``, the self-hosted vLLM/SGLang endpoint
  from the Hy3 repository README; Tencent Cloud's OpenAI-compatible endpoint
  goes in the same variable)
* else                             → **FAKE** with a prominent
  "OFFLINE DEMO MODE (fake Hy3 backend)" banner.

No secret is ever hardcoded: in FAKE mode the api_key is the literal
``"OFFLINE"`` and never leaves the process (the fake transport is in-process).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Mapping

DEFAULT_API_BASE = "http://127.0.0.1:8000/v1"  # self-hosted vLLM endpoint (Hy3 repo README)
DEFAULT_MODEL = "hy3"
DEFAULT_TEMPERATURE = 0.9  # Hy3 repo README recommended value
DEFAULT_TOP_P = 1.0        # Hy3 repo README recommended value
DEFAULT_TIMEOUT = 60.0
DEFAULT_MAX_FIX_RETRIES = 2
FAKE_API_KEY = "OFFLINE"


class BackendMode(str, Enum):
    """Which Hy3 backend the process talks to."""

    REAL = "real"
    FAKE = "fake"


@dataclass(frozen=True)
class Settings:
    """Immutable runtime configuration resolved from the environment."""

    mode: BackendMode
    api_base: str
    api_key: str
    model: str
    temperature: float
    top_p: float
    reasoning_effort: str | None
    request_timeout: float
    max_fix_retries: int
    auto_yes: bool
    home_dir: Path

    @classmethod
    def from_env(
        cls,
        env: Mapping[str, str] | None = None,
        *,
        offline: bool = False,
        auto_yes: bool = False,
    ) -> "Settings":
        """Build settings from ``env`` (defaults to ``os.environ``).

        ``offline`` / ``auto_yes`` mirror the ``--offline`` / ``--yes`` CLI
        flags and take precedence over the environment.
        """
        e = os.environ if env is None else env
        forced_offline = offline or e.get("HYSHELL_OFFLINE", "") not in ("", "0")
        api_key = e.get("HY3_API_KEY", "")
        if forced_offline or not api_key:
            mode, api_key = BackendMode.FAKE, FAKE_API_KEY
        else:
            mode = BackendMode.REAL
        home_env = e.get("HYSHELL_HOME", "")
        # expand ~ and $VARs — .env.example/README document HYSHELL_HOME=~/.hyshell
        home = (
            Path(os.path.expanduser(os.path.expandvars(home_env)))
            if home_env
            else Path.home() / ".hyshell"
        )
        return cls(
            mode=mode,
            api_base=e.get("HY3_API_BASE", DEFAULT_API_BASE),
            api_key=api_key,
            model=e.get("HY3_MODEL", DEFAULT_MODEL),
            temperature=float(e.get("HY3_TEMPERATURE", DEFAULT_TEMPERATURE)),
            top_p=float(e.get("HY3_TOP_P", DEFAULT_TOP_P)),
            reasoning_effort=e.get("HY3_REASONING_EFFORT") or None,
            request_timeout=float(e.get("HY3_TIMEOUT", DEFAULT_TIMEOUT)),
            max_fix_retries=int(e.get("HYSHELL_MAX_FIX_RETRIES", DEFAULT_MAX_FIX_RETRIES)),
            auto_yes=auto_yes,
            home_dir=home,
        )

    @property
    def is_offline(self) -> bool:
        """True when running against the built-in deterministic fake backend."""
        return self.mode is BackendMode.FAKE

    def masked_key(self) -> str:
        """Key rendered safe for display (never print the real secret)."""
        if self.mode is BackendMode.FAKE:
            return "(offline — no key needed)"
        if len(self.api_key) <= 8:
            return "***"
        return f"{self.api_key[:4]}…{self.api_key[-2:]} (masked)"
