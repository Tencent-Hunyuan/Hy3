"""Adapter base class + registry.

Adding a new agent = create `adapters/<name>.py` subclassing `AgentAdapter` and
decorating it with `@register`. The core engine never changes (DESIGN.md §6).
"""
from __future__ import annotations

import importlib
import pkgutil
from abc import ABC, abstractmethod
from pathlib import Path

from ctxpilot.models import SessionTranscript

_REGISTRY: dict[str, type["AgentAdapter"]] = {}


def register(cls: type["AgentAdapter"]) -> type["AgentAdapter"]:
    if not getattr(cls, "name", None):
        raise ValueError(f"Adapter {cls.__name__} must define a `name`")
    _REGISTRY[cls.name] = cls
    return cls


class AgentAdapter(ABC):
    # Subclasses set a unique lowercase `name`, e.g. "opencode".
    name: str

    @abstractmethod
    def session_dir(self) -> Path:
        """Root directory where this agent stores its sessions (read-only)."""

    @abstractmethod
    def discover_sessions(self) -> list[Path]:
        """Return paths to all sessions found under `session_dir`."""

    @abstractmethod
    def parse_session(self, path: Path) -> SessionTranscript:
        """Parse one session file into a normalized SessionTranscript."""


def discover_adapters() -> dict[str, type[AgentAdapter]]:
    """Import every adapter module in this package to populate the registry."""
    import ctxpilot.adapters as pkg

    for mod in pkgutil.iter_modules(pkg.__path__):
        if mod.name in ("base", "__init__"):
            continue
        importlib.import_module(f"ctxpilot.adapters.{mod.name}")
    return dict(_REGISTRY)


def get_adapter(name: str) -> AgentAdapter:
    if not _REGISTRY:
        discover_adapters()
    if name not in _REGISTRY:
        raise KeyError(f"Unknown agent adapter: {name!r}. Available: {sorted(_REGISTRY)}")
    return _REGISTRY[name]()


def list_adapters() -> list[str]:
    if not _REGISTRY:
        discover_adapters()
    return sorted(_REGISTRY)
