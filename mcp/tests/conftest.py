"""Shared pytest fixtures."""

from __future__ import annotations

import os

import pytest


@pytest.fixture
def hunyuan_env(monkeypatch):
    """Set a dummy HUNYUAN_API_KEY for tests that build a Config/server."""
    monkeypatch.setenv("HUNYUAN_API_KEY", "test-key")
    # Ensure no Tavily key so the DuckDuckGo path is used by default.
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    return "test-key"
