# Copyright (C) 2026 Tencent. Licensed under the Apache License, Version 2.0.
# SPDX-License-Identifier: Apache-2.0
"""Real command execution: ``bash -c`` with timeout protection and capture."""

from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path

from hyshell.schema import ExecutionResult

DEFAULT_EXEC_TIMEOUT = 30.0
OUTPUT_LIMIT = 4000
TIMEOUT_EXIT_CODE = 124  # same convention as GNU timeout(1)
EXEC_ERROR_EXIT_CODE = 126  # runner-level failure (spawn/decode error) — bash "cannot execute" convention


def _truncate(text: str, limit: int = OUTPUT_LIMIT) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n…(输出过长,已截断 truncated)"


def run_command(
    command: str,
    *,
    cwd: Path,
    timeout: float = DEFAULT_EXEC_TIMEOUT,
) -> ExecutionResult:
    """Execute ``command`` via ``/bin/bash -c`` in ``cwd``.

    * captures stdout/stderr (each truncated to ~4000 chars);
    * runs the command in its own session (``start_new_session=True``) so a
      timeout SIGKILLs the whole process group — pipeline children included —
      not just the bash parent (exit code 124, ``timed_out=True``);
    * pins ``LC_ALL``/``LANG`` to ``C.UTF-8`` so output is locale-stable;
    * decodes output as UTF-8 with ``errors="replace"`` — commands that emit
      non-UTF-8 bytes (binaries, mixed encodings) yield U+FFFD replacement
      characters instead of an uncaught ``UnicodeDecodeError``.
    """
    env = dict(os.environ)
    env["LC_ALL"] = "C.UTF-8"
    env["LANG"] = "C.UTF-8"
    started = time.monotonic()
    proc = subprocess.Popen(
        ["/bin/bash", "-c", command],
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",  # never crash the session on non-UTF-8 output
        env=env,
        start_new_session=True,  # own process group → group-wide timeout kill
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        return ExecutionResult(
            command=command,
            exit_code=proc.returncode,
            stdout=_truncate(stdout),
            stderr=_truncate(stderr),
            duration_s=time.monotonic() - started,
        )
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):  # pragma: no cover - already gone
            proc.kill()
        stdout, stderr = proc.communicate()
        return ExecutionResult(
            command=command,
            exit_code=TIMEOUT_EXIT_CODE,
            stdout=_truncate(stdout or ""),
            stderr=_truncate(stderr or ""),
            duration_s=time.monotonic() - started,
            timed_out=True,
        )
