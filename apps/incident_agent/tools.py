from __future__ import annotations

import asyncio
import os
import signal
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


def _workspace_files(root: Path, pattern: str = "*") -> list[Path]:
    resolved_root = root.resolve()
    files = []
    for path in root.rglob(pattern):
        if path.is_symlink():
            continue
        try:
            resolved = path.resolve(strict=True)
        except OSError:
            continue
        if resolved.is_relative_to(resolved_root) and resolved.is_file():
            files.append(path)
    return sorted(files)


def list_files(root: Path) -> ToolResult:
    lines = []
    for path in _workspace_files(root):
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
    for path in _workspace_files(root):
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


def _check_command(root: Path, check: str) -> list[str] | ToolResult:
    if check == "pytest":
        return [sys.executable, "-m", "pytest", "-q"]
    if check == "py_compile":
        python_files = [
            path.relative_to(root).as_posix()
            for path in _workspace_files(root, "*.py")
        ]
        if not python_files:
            return ToolResult(False, "No Python files were provided.")
        return [sys.executable, "-m", "py_compile", *python_files]
    return ToolResult(False, f"Unsupported check: {check}")


def _completed_result(returncode: int, stdout: str, stderr: str) -> ToolResult:
    output = "\n".join(part.strip() for part in (stdout, stderr) if part.strip())
    return ToolResult(
        returncode == 0,
        bounded(output or "Check completed with no output."),
    )


def run_checks(root: Path, check: str) -> ToolResult:
    command = _check_command(root, check)
    if isinstance(command, ToolResult):
        return command

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

    return _completed_result(
        completed.returncode,
        completed.stdout,
        completed.stderr,
    )


async def _terminate_process_tree(process: asyncio.subprocess.Process) -> None:
    if process.returncode is not None:
        return
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
    except ProcessLookupError:
        pass
    await process.wait()


async def async_run_checks(
    root: Path,
    check: str,
    timeout_seconds: float = 20,
) -> ToolResult:
    command = _check_command(root, check)
    if isinstance(command, ToolResult):
        return command

    process_options: dict[str, Any] = {}
    if os.name == "posix":
        process_options["start_new_session"] = True
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=root,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=safe_environment(),
            **process_options,
        )
    except OSError:
        return ToolResult(False, "Check could not be started.")

    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout_seconds,
        )
    except TimeoutError:
        await _terminate_process_tree(process)
        return ToolResult(
            False,
            f"Check timed out after {timeout_seconds:g} seconds.",
        )
    except asyncio.CancelledError:
        await _terminate_process_tree(process)
        raise

    return _completed_result(
        process.returncode or 0,
        stdout_bytes.decode("utf-8", errors="replace"),
        stderr_bytes.decode("utf-8", errors="replace"),
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


async def execute_tool_async(
    root: Path,
    name: str,
    arguments: dict[str, Any],
    timeout_seconds: float = 20,
) -> ToolResult:
    if name != "run_checks":
        return execute_tool(root, name, arguments)
    if not isinstance(arguments, dict):
        return ToolResult(False, "Invalid arguments for run_checks: arguments must be an object")
    check = arguments.get("check")
    if not isinstance(check, str):
        return ToolResult(False, "Invalid arguments for run_checks: check must be a string")
    return await async_run_checks(root, check, timeout_seconds)


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
