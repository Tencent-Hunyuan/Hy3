# Copyright (C) 2026 Tencent. Licensed under the Apache License, Version 2.0.
# SPDX-License-Identifier: Apache-2.0
"""JSONL session history (``$HYSHELL_HOME/history.jsonl``, default ``~/.hyshell/``)."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from hyshell.schema import TurnRecord


class HistoryStore:
    """Append-only JSONL store for :class:`TurnRecord` entries."""

    def __init__(self, home_dir: Path) -> None:
        self.home_dir = Path(home_dir)
        self.path = self.home_dir / "history.jsonl"

    def append(self, record: TurnRecord) -> None:
        self.home_dir.mkdir(parents=True, exist_ok=True)
        payload = asdict(record)
        payload["risk_final"] = record.risk_final.name if record.risk_final is not None else None
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def load_last(self, n: int = 10) -> list[dict]:
        """Return the most recent ``n`` entries (oldest first); skips corrupt lines."""
        if not self.path.exists():
            return []
        entries: list[dict] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # tolerate a torn write; history is best-effort
        return entries[-n:]
