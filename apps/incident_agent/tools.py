from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MAX_OBSERVATION_CHARS = 12_000
MAX_SEARCH_MATCHES = 80
MAX_READ_LINES = 300


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    content: str


def bounded(text: str, limit: int = MAX_OBSERVATION_CHARS) -> str:
    if len(text) <= limit:
        return text
    suffix = "\n...[output truncated]"
    return text[: limit - len(suffix)] + suffix


def _safe_path(root: Path, relative_path: str) -> Path:
    if not relative_path or Path(relative_path).is_absolute():
        raise ValueError("Path must be a nonempty relative path.")
    resolved_root = root.resolve()
    resolved = (resolved_root / relative_path).resolve()
    if not resolved.is_relative_to(resolved_root):
        raise ValueError("Path escapes the incident workspace.")
    return resolved


def list_files(root: Path) -> ToolResult:
    lines = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root)
        lines.append(f"{relative.as_posix()} ({path.stat().st_size} bytes)")
    return ToolResult(True, bounded("\n".join(lines) or "No files found."))


def search_files(
    root: Path,
    query: str,
    extensions: list[str] | None = None,
) -> ToolResult:
    if not query:
        return ToolResult(False, "Search query must not be blank.")
    normalized_extensions = None
    if extensions:
        normalized_extensions = {
            extension.lower() if extension.startswith(".") else f".{extension.lower()}"
            for extension in extensions
        }

    matches: list[str] = []
    needle = query.casefold()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if normalized_extensions and path.suffix.lower() not in normalized_extensions:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for line_number, line in enumerate(lines, start=1):
            if needle in line.casefold():
                relative = path.relative_to(root).as_posix()
                matches.append(f"{relative}:{line_number}: {line}")
                if len(matches) >= MAX_SEARCH_MATCHES:
                    return ToolResult(
                        True,
                        bounded("\n".join(matches) + "\n...[match limit reached]"),
                    )

    return ToolResult(True, bounded("\n".join(matches) or "No matches found."))


def read_file(
    root: Path,
    path: str,
    start_line: int = 1,
    end_line: int = 200,
) -> ToolResult:
    try:
        resolved = _safe_path(root, path)
    except ValueError as exc:
        return ToolResult(False, str(exc))
    if not resolved.is_file():
        return ToolResult(False, f"File not found: {path}")
    if start_line < 1 or end_line < start_line:
        return ToolResult(False, "Line range must be positive and ordered.")

    try:
        lines = resolved.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return ToolResult(False, f"Unable to read UTF-8 file: {path}")
    if start_line > len(lines) and lines:
        return ToolResult(False, f"Start line exceeds file length: {path}")

    bounded_end = min(end_line, start_line + MAX_READ_LINES - 1, len(lines))
    selected = [
        f"{line_number}: {lines[line_number - 1]}"
        for line_number in range(start_line, bounded_end + 1)
    ]
    body = "\n".join(selected) or "File is empty."
    return ToolResult(True, bounded(f"File: {path}\n{body}"))


def safe_environment() -> dict[str, str]:
    return {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    }


def run_checks(root: Path, check: str) -> ToolResult:
    if check == "pytest":
        command = [sys.executable, "-m", "pytest", "-q"]
    elif check == "py_compile":
        python_files = sorted(
            path.relative_to(root).as_posix() for path in root.rglob("*.py")
        )
        if not python_files:
            return ToolResult(False, "No Python files were provided.")
        command = [sys.executable, "-m", "py_compile", *python_files]
    else:
        return ToolResult(False, f"Unsupported check: {check}")

    try:
        completed = subprocess.run(
            command,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=20,
            env=safe_environment(),
            check=False,
        )
    except subprocess.TimeoutExpired:
        return ToolResult(False, "Check timed out after 20 seconds.")
    except OSError:
        return ToolResult(False, "Check could not be started.")

    output = "\n".join(
        part.strip() for part in (completed.stdout, completed.stderr) if part.strip()
    )
    return ToolResult(
        completed.returncode == 0,
        bounded(output or "Check completed with no output."),
    )


def _integer(arguments: dict[str, Any], key: str, default: int) -> int:
    value = arguments.get(key, default)
    if type(value) is not int:
        raise ValueError(f"{key} must be an integer")
    return value


def execute_tool(
    root: Path,
    name: str,
    arguments: dict[str, Any],
) -> ToolResult:
    try:
        if not isinstance(arguments, dict):
            raise ValueError("arguments must be an object")
        if name == "list_files":
            return list_files(root)
        if name == "search_files":
            query = arguments.get("query")
            extensions = arguments.get("extensions")
            if not isinstance(query, str):
                raise ValueError("query must be a string")
            if extensions is not None and (
                not isinstance(extensions, list)
                or not all(isinstance(item, str) for item in extensions)
            ):
                raise ValueError("extensions must be an array of strings")
            return search_files(root, query, extensions)
        if name == "read_file":
            path = arguments.get("path")
            if not isinstance(path, str):
                raise ValueError("path must be a string")
            return read_file(
                root,
                path,
                _integer(arguments, "start_line", 1),
                _integer(arguments, "end_line", 200),
            )
        if name == "run_checks":
            check = arguments.get("check")
            if not isinstance(check, str):
                raise ValueError("check must be a string")
            return run_checks(root, check)
        return ToolResult(False, f"Unknown tool: {name}")
    except (TypeError, ValueError) as exc:
        return ToolResult(False, f"Invalid arguments for {name}: {exc}")


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List incident workspace files and their sizes.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search text files for a literal case-insensitive query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "extensions": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a bounded line range from one workspace file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "start_line": {"type": "integer", "minimum": 1},
                    "end_line": {"type": "integer", "minimum": 1},
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_checks",
            "description": "Run one allowlisted check in the trusted incident workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "check": {"type": "string", "enum": ["pytest", "py_compile"]},
                },
                "required": ["check"],
                "additionalProperties": False,
            },
        },
    },
]
