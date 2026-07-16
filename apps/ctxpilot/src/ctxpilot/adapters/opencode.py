"""OpenCode adapter — reads ~/.local/share/opencode/opencode.db (READ-ONLY).

OpenCode keeps its real session history in a SQLite database (``opencode.db``).
The schema has several tables; the ones we care about:

  - ``session``    : id, directory (absolute project path!), title
  - ``message``    : id, session_id, data — each row is ONE conversation message.
                     ``data`` is JSON with ``role`` ("user"/"assistant"/"system")
                     and a nested ``parts`` array (text / tool-call parts).
  - ``part``       : message_id, session_id, data — low-level parts (text,
                     tool_call, step-start, ...). We walk these for content +
                     touched files.
  - ``session_message`` : lightweight EVENT markers ({"agent":"build"}, ...).
                     We do NOT use these for content — they carry no text.

Only the real ``message``+``part`` tables give us conversation content (preview +
HANDOFF quality) and touched files. We ONLY read the DB (DESIGN.md §8 S4) and
mirror each session into our own cache (``~/.ctxpilot/cache/opencode/<id>.json``)
so the monitor can diff by mtime without re-querying the DB every poll.
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from ctxpilot.adapters.base import AgentAdapter, register
from ctxpilot.models import Message, SessionTranscript

_CACHE_DIR = Path.home() / ".ctxpilot" / "cache" / "opencode"

_PATH_HINTS = ("path", "file_path", "filename", "abs_path", "file", "root")


def _paths_from_tool(tc: dict) -> set[str]:
    """Best-effort extraction of absolute file paths from an opencode tool call."""
    out: set[str] = set()
    args = tc.get("arguments") or tc.get("input") or tc.get("parameters")
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except (json.JSONDecodeError, ValueError):
            args = None
    if isinstance(args, dict):
        for k, v in args.items():
            if any(h in k.lower() for h in _PATH_HINTS) and isinstance(v, str) and os.path.isabs(v):
                out.add(v)
    nested = tc.get("tool") or tc.get("function")
    if isinstance(nested, dict):
        out.update(_paths_from_tool(nested))
    return out


def _normalize_tool_call(p: dict) -> dict:
    """Flatten opencode's various tool_call part shapes into {name, arguments}."""
    tc = p.get("tool_call") or p.get("toolCall") or p.get("function") or p
    if not isinstance(tc, dict):
        return {"name": "", "arguments": {}}
    name = tc.get("name")
    args = tc.get("arguments") or tc.get("input") or tc.get("parameters")
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except (json.JSONDecodeError, ValueError):
            args = {}
    if not isinstance(args, (dict, list)):
        args = {}
    return {"name": name or "", "arguments": args}


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
            try:
                blob = self._build_cache_blob(conn, sid, directory, title)
            except sqlite3.Error:
                blob = None
            if blob is None:
                continue
            cache = _CACHE_DIR / f"{sid}.json"
            # Only rewrite when content changed -> keeps mtime stable for monitoring.
            if not (cache.exists() and cache.read_text(encoding="utf-8") == blob):
                cache.write_text(blob, encoding="utf-8")
            paths.append(cache)
        return sorted(paths)

    def _build_cache_blob(self, conn, sid: str, directory: str, title) -> str | None:
        """Read real conversation (message + part) for one session and serialize."""
        try:
            msg_rows = conn.execute(
                "SELECT id, data FROM message WHERE session_id=? ORDER BY time_created",
                (sid,),
            ).fetchall()
        except sqlite3.Error:
            return None
        messages: list[dict] = []
        for mid, mdata in msg_rows:
            try:
                m = json.loads(mdata) if isinstance(mdata, str) else mdata
            except (json.JSONDecodeError, ValueError):
                m = {}
            role = m.get("role")
            if not role:
                continue
            parts = []
            try:
                for (pdata,) in conn.execute(
                    "SELECT data FROM part WHERE message_id=? ORDER BY time_created",
                    (mid,),
                ):
                    try:
                        parts.append(json.loads(pdata) if isinstance(pdata, str) else pdata)
                    except (json.JSONDecodeError, ValueError):
                        continue
            except sqlite3.Error:
                parts = []
            text_parts: list[str] = []
            tool_calls: list[dict] = []
            for p in parts:
                if not isinstance(p, dict):
                    continue
                ptype = p.get("type")
                if ptype == "text":
                    text_parts.append(p.get("text", "") or "")
                elif ptype in ("tool_call", "tool-call"):
                    tc = _normalize_tool_call(p)
                    tool_calls.append(tc)
            content = "\n".join(text_parts).strip()
            if content or tool_calls:
                messages.append(
                    {"role": role, "content": content, "tool_calls": tool_calls}
                )
        return json.dumps(
            {"id": sid, "directory": directory, "title": title or "", "messages": messages},
            ensure_ascii=False,
        )

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
        for m in data.get("messages", []):
            role = m.get("role")
            content = m.get("content", "")
            if not role:
                continue
            tcs = m.get("tool_calls", []) or []
            norm_tcs = []
            for tc in tcs:
                if isinstance(tc, dict):
                    norm_tcs.append(
                        {"name": tc.get("name", ""), "arguments": tc.get("arguments", {})}
                    )
                    files.update(_paths_from_tool(tc))
            if content or norm_tcs:
                messages.append(Message(role=role, content=str(content), tool_calls=norm_tcs))
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
