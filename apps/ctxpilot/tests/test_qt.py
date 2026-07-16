"""Qt client smoke test — skipped when PySide6 is not installed.

We don't need a display to validate that the module imports and the facade
wiring is correct. When PySide6 is present, we also build the window headless.
"""
from __future__ import annotations

import pytest

try:
    from ctxpilot.qt.app import MainWindow, SettingsDialog, Worker, run_qt  # noqa: F401
    HAVE_QT = True
except ImportError:
    HAVE_QT = False

pytestmark = pytest.mark.skipif(not HAVE_QT, reason="PySide6 not installed")


def test_worker_emits_result():
    import threading

    w = Worker(lambda: 42)
    got = {}
    w.done.connect(lambda r: got.setdefault("r", r))
    w.start()
    w.wait(2000)
    assert got.get("r") == 42


def test_window_builds_without_display():
    from ctxpilot.config import Config
    from ctxpilot.core import CtxPilot

    cp = CtxPilot(Config(hy3_api_key="k", hy3_base_url="http://x"))
    win = MainWindow(cp)
    # surface-level sanity: widgets exist
    assert win.proj_list is not None
    assert win.agent_sel is not None


def test_cli_qt_command_guard(monkeypatch):
    # Ensure `ctxpilot qt` without PySide6 prints a friendly hint, not a crash.
    import ctxpilot.cli as cli

    # Force the import failure path
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name.startswith("PySide6"):
            raise ImportError("no PySide6")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(SystemExit) as ei:
        cli.qt()
    assert ei.value.code == 2
