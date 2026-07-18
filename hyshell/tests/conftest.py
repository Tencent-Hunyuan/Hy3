# Copyright (C) 2026 Tencent. Licensed under the Apache License, Version 2.0.
# SPDX-License-Identifier: Apache-2.0
"""Shared fixtures. Injects src/ (and the project root, for demo/) into sys.path
so the suite runs without installation."""

from __future__ import annotations

import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for entry in (str(ROOT / "src"), str(ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import httpx  # noqa: E402
import pytest  # noqa: E402
from rich.console import Console  # noqa: E402

from hyshell.config import Settings  # noqa: E402
from hyshell.executor import run_command  # noqa: E402
from hyshell.fake_backend import make_fake_transport  # noqa: E402


def make_recorded_console() -> Console:
    """Same console profile as the GIF recorder (80 cols, truecolor, no tty)."""
    return Console(
        record=True,
        force_terminal=True,
        width=80,
        color_system="truecolor",
        file=io.StringIO(),
    )


class SpyTransport(httpx.BaseTransport):
    """Records every request before delegating to the fake backend."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self._inner = make_fake_transport()

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self._inner.handle_request(request)


class SpyRunner:
    """Wraps the real executor, recording every executed command."""

    def __init__(self) -> None:
        self.commands: list[str] = []

    def __call__(self, command: str, *, cwd, timeout: float = 30.0):
        self.commands.append(command)
        return run_command(command, cwd=cwd, timeout=timeout)


@pytest.fixture
def spy_transport() -> SpyTransport:
    return SpyTransport()


@pytest.fixture
def spy_runner() -> SpyRunner:
    return SpyRunner()


@pytest.fixture
def offline_settings(tmp_path: Path) -> Settings:
    return Settings.from_env({"HYSHELL_HOME": str(tmp_path / "home")}, offline=True)


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    from hyshell.demo_flows import setup_workspace

    ws = tmp_path / "workspace"
    setup_workspace(ws)
    return ws


@pytest.fixture
def recorded_console() -> Console:
    return make_recorded_console()


@pytest.fixture
def make_app(tmp_path: Path):
    """Factory: scripted-input app wired to the offline fake backend."""
    from hyshell.app import ShellAssistantApp
    from hyshell.tui import ScriptedInput

    def _make(
        inputs,
        *,
        workdir: Path,
        auto_yes: bool = False,
        runner=None,
        console: Console | None = None,
    ):
        console = console or make_recorded_console()
        settings = Settings.from_env(
            {"HYSHELL_HOME": str(tmp_path / "home")}, offline=True, auto_yes=auto_yes
        )
        app = ShellAssistantApp(
            settings=settings,
            console=console,
            input_source=ScriptedInput(list(inputs), console=console),
            workdir=workdir,
            runner=runner,
        )
        return app, console

    return _make
