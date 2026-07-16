"""Codex (OpenAI CLI) adapter — reads ~/.codex/sessions/**/rollout-*.jsonl (read-only).

The Codex CLI writes each session as a JSONL file of events. We only READ these;
`codex resume` replays the same files, so this is safe and non-intrusive.

Real Codex rollout format (observed):
  - First event is {"type":"session_meta","payload":{...,"cwd":"C:\\...","id":"..."}}
  - Subsequent events wrap their data in a "payload" object, e.g.
    {"type":"response_item","payload":{"type":"message","role":"...","content":[...]}}
    {"type":"response_item","payload":{"type":"function_call","name":"...","arguments":"..."}}
  - "cwd" can appear at the top level OR nested in payload. We capture it from
    session_meta so the dashboard can place the session under its real project
    directory WITHOUT the user typing anything.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ctxpilot.adapters.base import AgentAdapter, register
from ctxpilot.models import Message, SessionTranscript

_FILE_EXT = (
    ".py", ".ts", ".go", ".md", ".json", ".js", ".rs", ".java", ".c", ".cpp",
    ".h", ".txt", ".yaml", ".yml", ".toml", ".sh", ".cfg", ".toml",
)


@register
class CodexAdapter(AgentAdapter):
    name = "codex"

    def session_dir(self) -> Path:
        return Path.home() / ".codex" / "sessions"

    def discover_sessions(self) -> list[Path]:
        d = self.session_dir()
        if not d.exists():
            return []
        return sorted(d.rglob("rollout-*.jsonl"))

    @staticmethod
    def _extract_text(content) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            out = []
            for part in content:
                if isinstance(part, dict):
                    out.append(
                        part.get("text") or part.get("input_text") or part.get("output_text") or ""
                    )
                elif isinstance(part, str):
                    out.append(part)
            return "\n".join(x for x in out if x)
        return str(content)

    @staticmethod
    def _collect_paths(text: str, files: set[str]) -> None:
        """Heuristically pull file-path tokens out of tool-call arguments etc."""
        if not isinstance(text, str):
            return
        for tok in re.split(r'[\s"\'`,;(){}\[\]<>]+', text):
            t = tok.strip()
            if not t.endswith(_FILE_EXT):
                continue
            # require it to actually look like a path
            if "/" in t or "\\" in t or ":" in t or t.startswith((".", "~")):
                files.add(t)

    def parse_session(self, path: Path) -> SessionTranscript:
        messages: list[Message] = []
        files: set[str] = set()
        cwd: str | None = None
        sid = Path(path).stem
        for raw in Path(path).read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                ev = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(ev, dict):
                continue
            etype = ev.get("type")
            payload = ev.get("payload") if isinstance(ev.get("payload"), dict) else ev

            # --- project directory (authoritative: session_meta.payload.cwd) ---
            if cwd is None:
                c = ev.get("cwd") or (ev.get("payload") or {}).get("cwd")
                if isinstance(c, str) and c.strip():
                    cwd = c.strip()

            # --- session id (use the real id over the filename) ---
            if etype == "session_meta":
                pid = (ev.get("payload") or {}).get("id")
                if pid:
                    sid = str(pid)

            # --- messages / assistant content ---
            content = payload.get("content") if isinstance(payload, dict) else None
            role = payload.get("role") if isinstance(payload, dict) else None
            if content is None:
                content = ev.get("content")
            if role is None:
                role = ev.get("role")
            text = self._extract_text(content)
            if role and text:
                messages.append(Message(role=role, content=text, ts=ev.get("timestamp")))

            # --- tool calls -> capture file references ---
            if isinstance(payload, dict):
                ptype = payload.get("type")
                if ptype in ("function_call", "tool_call", "exec_command", "exec"):
                    args = payload.get("arguments") or payload.get("args") or ""
                    name = payload.get("name") or ptype
                    messages.append(Message(role="assistant", content=f"[{name}] {args}"))
                    self._collect_paths(args if isinstance(args, str) else json.dumps(args), files)
                # also scan the whole payload for path-like strings
                self._collect_paths(json.dumps(payload), files)

        if cwd is None:
            cwd = self._project_path_from_args(messages)
        return SessionTranscript(
            agent="codex",
            session_id=sid,
            messages=messages,
            files_touched=sorted(files),
            project_path=cwd,
        )

    @staticmethod
    def _project_path_from_args(messages: list[Message]) -> str | None:
        """Last resort: find an absolute path in shell-like tool calls."""
        for m in reversed(messages):
            for tok in re.split(r'[\s"\'`,;(){}\[\]<>]+', m.content):
                t = tok.strip()
                if t.startswith("/") or (len(t) > 2 and t[1] == ":" and t[2] == "\\"):
                    if not t.endswith(_FILE_EXT):
                        return t
        return None
