"""OpenCode adapter — reads ~/.local/share/opencode/opencode.db (READ-ONLY).

OpenCode keeps its real session history in a SQLite database (``opencode.db``):
  - ``session`` table: id, project_id, directory (absolute project path!), title
  - ``session_message`` table: session_id, seq, data (JSON message payload)

We ONLY read this database — we never write to it (DESIGN.md §8 S4). To keep the
rest of the pipeline (scanner/monitor) unchanged, each DB session is mirrored into
OUR OWN cache directory (``~/.ctxpilot/cache/opencode/<id>.json``). The cache file's
mtime drives change-detection; we only rewrite it when the session actually changed,
so the live monitor doesn't flood the feed.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from ctxpilot.adapters.base import AgentAdapter, register
from ctxpilot.models import Message, SessionTranscript

_CACHE_DIR = Path.home() / ".ctxpilot" / "cache" / "opencode"


@register
class OpenCodeAdapter(AgentAdapter):
    name = "opencode"

    def session_dir(self) -> Path:
        return Path.home() / ".local" / "share" / "opencode"

    def db_path(self) -> Path:
        return self.session_dir() / "opencode.db"

    def discover_sessions(self) -> list[Path]:
        db = self.db_path()
        if db.exists():
            try:
                return self._discover_from_db(db)
            except Exception:
                pass
        # Fallback: legacy JSON session files (if any exist).
        found: set[Path] = set()
        for pattern in ("storage/session/*.json", "sessions/*.json"):
            found.update(self.session_dir().glob(pattern))
        return sorted(p for p in found if p.name.lower() != "auth.json")

    def _discover_from_db(self, db: Path) -> list[Path]:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            rows = conn.execute(
                "SELECT id, directory, title FROM session WHERE directory IS NOT NULL"
            ).fetchall()
        except sqlite3.Error:
            return []
        paths: list[Path] = []
        for sid, directory, title in rows:
            messages = []
            try:
                for (data,) in conn.execute(
                    "SELECT data FROM session_message WHERE session_id=? ORDER BY seq",
                    (sid,),
                ):
                    messages.append(data)
            except sqlite3.Error:
                pass
            cache = _CACHE_DIR / f"{sid}.json"
            blob = json.dumps(
                {"id": sid, "directory": directory, "title": title, "messages": messages},
                ensure_ascii=False,
            )
            # Only rewrite when content changed -> keeps mtime stable for monitoring.
            if not (cache.exists() and cache.read_text(encoding="utf-8") == blob):
                cache.write_text(blob, encoding="utf-8")
            paths.append(cache)
        return sorted(paths)

    def parse_session(self, path: Path) -> SessionTranscript:
        # Our mirrored cache files
        if path.parent == _CACHE_DIR:
            return self._parse_cache(path)
        # Legacy JSON session file
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, ValueError):
            return SessionTranscript(agent="opencode", session_id=Path(path).stem)
        if not isinstance(data, dict):
            return SessionTranscript(agent="opencode", session_id=Path(path).stem)
        sid = str(data.get("id") or data.get("sessionId") or Path(path).stem)
        messages: list[Message] = []
        files: set[str] = set()
        for m in data.get("messages", []):
            role = m.get("role", "user")
            content = m.get("content", "")
            if isinstance(content, list):
                content = "\n".join(p.get("text", "") for p in content if isinstance(p, dict))
            tool_calls = m.get("toolCalls") or m.get("tool_calls") or []
            for tc in tool_calls:
                for f in (tc.get("files") or []):
                    files.add(f)
            messages.append(Message(role=role, content=str(content)))
        return SessionTranscript(
            agent="opencode",
            session_id=sid,
            messages=messages,
            files_touched=sorted(files),
            started_at=data.get("createdAt"),
            ended_at=data.get("updatedAt"),
            project_path=self._project_path_of(data),
        )

    def _parse_cache(self, path: Path) -> SessionTranscript:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        sid = str(data.get("id") or Path(path).stem)
        directory = data.get("directory")
        messages: list[Message] = []
        files: set[str] = set()
        for raw in data.get("messages", []):
            try:
                m = json.loads(raw) if isinstance(raw, str) else raw
            except (json.JSONDecodeError, ValueError):
                continue
            if not isinstance(m, dict):
                continue
            role = m.get("role") or m.get("type")
            content = m.get("content")
            if isinstance(content, list):
                text = "\n".join(
                    p.get("text", "") for p in content if isinstance(p, dict)
                )
            else:
                text = content or ""
            if role and text:
                messages.append(Message(role=role, content=str(text)))
        return SessionTranscript(
            agent="opencode",
            session_id=sid,
            messages=messages,
            files_touched=sorted(files),
            project_path=directory,
        )

    @staticmethod
    def _project_path_of(data: dict) -> str | None:
        for key in ("cwd", "workspacePath", "projectPath", "rootPath", "directory", "workspace"):
            v = data.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
        return None
