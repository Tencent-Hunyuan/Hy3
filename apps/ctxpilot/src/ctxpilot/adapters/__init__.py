"""Agent adapters package.

Importing this package does NOT auto-import adapter implementations. Use
`discover_adapters()` to populate the registry (DESIGN.md §3.2 / §6).
"""
from ctxpilot.adapters.base import (
    AgentAdapter,
    discover_adapters,
    get_adapter,
    list_adapters,
    register,
)

__all__ = ["AgentAdapter", "discover_adapters", "get_adapter", "list_adapters", "register"]
