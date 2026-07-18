# Copyright 2026 Tencent Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Environment-driven configuration for hy3-mcp.

Every knob comes from environment variables — nothing is hardcoded.  The
real API key deliberately never enters :class:`Settings` (only a boolean
``api_key_present`` flag), so it can never leak through ``repr``, logs or
the ``hy3_status`` tool.  The key itself is read from the environment only
at HTTP-client construction time (see :mod:`hy3_mcp.hy3_client`).

Mode selection (documented in the README, asserted in ``test_settings.py``):

1. ``HY3_MCP_OFFLINE`` truthy (or CLI ``--offline``)  → ``offline`` (forced).
2. else ``HY3_API_BASE`` or ``HY3_API_KEY`` set        → ``real``.
3. else (nothing configured)                           → ``offline`` with a
   stderr banner.  The server never crashes because a key is missing.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Mapping

__all__ = ["Settings", "DEFAULT_API_BASE", "REASONING_EFFORTS"]

#: Default OpenAI-compatible endpoint of a self-hosted Hy3
#: (vLLM / SGLang quickstart from the upstream README).
DEFAULT_API_BASE = "http://127.0.0.1:8000/v1"

#: Valid values for HY3_REASONING_EFFORT (upstream chat-template contract).
REASONING_EFFORTS = ("no_think", "low", "high")

_TRUTHY = {"1", "true", "yes", "on"}


def _flag(value: str | None) -> bool:
    return (value or "").strip().lower() in _TRUTHY


@dataclass(frozen=True)
class Settings:
    """Immutable, secret-free runtime configuration."""

    mode: Literal["offline", "real"]
    api_base: str
    api_key_present: bool
    model: str
    temperature: float
    top_p: float
    reasoning_effort: str | None
    timeout_seconds: float
    max_tokens: int
    root: Path
    docs_dir: Path
    search_provider: str

    @classmethod
    def from_env(
        cls,
        environ: Mapping[str, str] | None = None,
        *,
        force_offline: bool = False,
    ) -> "Settings":
        """Build settings from ``environ`` (default: ``os.environ``).

        ``force_offline`` mirrors the CLI ``--offline`` flag and wins over
        every environment variable.
        """
        env = os.environ if environ is None else environ

        offline_flag = force_offline or _flag(env.get("HY3_MCP_OFFLINE"))
        api_base_env = (env.get("HY3_API_BASE") or "").strip()
        api_key_present = bool((env.get("HY3_API_KEY") or "").strip())

        if offline_flag:
            mode: Literal["offline", "real"] = "offline"
        elif api_base_env or api_key_present:
            mode = "real"
        else:
            mode = "offline"

        effort_raw = (env.get("HY3_REASONING_EFFORT") or "").strip().lower()
        if effort_raw and effort_raw not in REASONING_EFFORTS:
            raise ValueError(
                f"HY3_REASONING_EFFORT={effort_raw!r} is invalid; "
                f"expected one of {', '.join(REASONING_EFFORTS)}"
            )

        root = Path(env.get("HY3_MCP_ROOT") or Path.cwd()).resolve()
        docs_raw = (env.get("HY3_MCP_DOCS_DIR") or "").strip()
        if docs_raw:
            docs_path = Path(docs_raw)
            docs_dir = (docs_path if docs_path.is_absolute() else root / docs_path).resolve()
        else:
            docs_dir = root

        return cls(
            mode=mode,
            api_base=api_base_env or DEFAULT_API_BASE,
            api_key_present=api_key_present,
            model=(env.get("HY3_MODEL") or "hy3").strip(),
            temperature=float(env.get("HY3_TEMPERATURE") or 0.9),
            top_p=float(env.get("HY3_TOP_P") or 1.0),
            reasoning_effort=effort_raw or None,
            timeout_seconds=float(env.get("HY3_TIMEOUT_SECONDS") or 120),
            max_tokens=int(env.get("HY3_MAX_TOKENS") or 2048),
            root=root,
            docs_dir=docs_dir,
            search_provider=(env.get("HY3_SEARCH_PROVIDER") or "offline").strip().lower(),
        )
