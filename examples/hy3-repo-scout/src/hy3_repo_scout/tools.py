"""Bounded, read-only tools for inspecting an untrusted repository."""

from __future__ import annotations

import codecs
import copy
import fnmatch
import hashlib
import os
import re
import shutil
import signal
import stat
import subprocess
import threading
import time
from collections import defaultdict
from collections.abc import Iterable, Iterator, Mapping
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

DEFAULT_MAX_FILE_BYTES = 256 * 1024
DEFAULT_MAX_READ_LINES = 400
DEFAULT_MAX_DIFF_CHARS = 120_000
MAX_LIST_LIMIT = 1_000
MAX_SEARCH_LIMIT = 200
MAX_SCANNED_FILES = 20_000
MAX_LINE_CHARS = 500
MAX_DIFF_PATHS = 1_000
MAX_GIT_NAME_BYTES = 512_000
MAX_GIT_DIFF_SECONDS = 20.0
MAX_GIT_OUTPUT_BYTES = 2_000_000
_BINARY_SAMPLE_BYTES = 8_192

_WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:[/\\]")
_VALID_REVISION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/@{}^~+\-]*$")
_SENSITIVE_NAMES = {
    ".env",
    ".git-credentials",
    ".netrc",
    ".npmrc",
    ".pypirc",
    "credentials",
    "credentials.json",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
    "secret",
    "secret.json",
    "secrets",
    "secrets.json",
}
_SENSITIVE_DIRECTORIES = {".aws", ".gnupg", ".ssh"}
_SENSITIVE_SUFFIXES = {".der", ".jks", ".key", ".keystore", ".p12", ".pfx", ".pem"}
_SENSITIVE_DATA_SUFFIXES = {".conf", ".ini", ".json", ".toml", ".txt", ".yaml", ".yml"}
_SENSITIVE_STEMS = {
    "credential",
    "credentials",
    "password",
    "passwords",
    "secret",
    "secrets",
    "token",
    "tokens",
}
_SAFE_ENV_TEMPLATES = {".env.example", ".env.sample", ".env.template"}
_SKIPPED_DIRECTORIES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "venv",
}
_SKIPPED_DIRECTORY_SUFFIXES = (".egg-info", ".dist-info")
_BLOCKED_PATH_PARTS = _SENSITIVE_DIRECTORIES | _SKIPPED_DIRECTORIES


class ToolError(ValueError):
    """A safe error that can be returned to the model without a traceback."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


@dataclass(frozen=True)
class _FileInfo:
    path: Path
    relative_path: str
    size: int


TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": (
                "List readable UTF-8 text files below a repository-relative path. Secret, "
                "binary, oversized, and unsafe symlink targets are omitted."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Repository-relative directory or file (default: .).",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Optional glob matched against repository-relative paths.",
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_LIST_LIMIT,
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_text",
            "description": (
                "Search readable UTF-8 repository files for a literal string and return line "
                "citations."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "minLength": 1},
                    "path": {"type": "string", "description": "Search root (default: .)."},
                    "pattern": {
                        "type": "string",
                        "description": "Optional repository-relative file glob.",
                    },
                    "case_sensitive": {"type": "boolean"},
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_SEARCH_LIMIT,
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
            "description": (
                "Read a bounded line range from a readable UTF-8 repository file. Lines are "
                "numbered for [path:Lx-Ly] citations."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Repository-relative file."},
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
            "name": "git_diff",
            "description": (
                "Return a bounded, no-external-helper Git diff while omitting secret, binary, "
                "oversized, and unsafe paths."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "base": {
                        "type": "string",
                        "description": "Commit or ref to compare against (default: HEAD).",
                    },
                    "path": {"type": "string", "description": "Optional repository path."},
                    "staged": {
                        "type": "boolean",
                        "description": "Compare the index rather than the working tree.",
                    },
                    "context_lines": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 20,
                    },
                    "max_chars": {
                        "type": "integer",
                        "minimum": 1_000,
                        "maximum": 200_000,
                    },
                },
                "additionalProperties": False,
            },
        },
    },
]


class RepoTools:
    """Expose a deliberately small, read-only view of one repository root."""

    def __init__(
        self,
        root: str | os.PathLike[str],
        *,
        max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
        max_read_lines: int = DEFAULT_MAX_READ_LINES,
    ) -> None:
        try:
            resolved_root = Path(root).expanduser().resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            message = "Repository root does not exist or is inaccessible."
            raise ToolError("invalid_root", message) from exc
        if not resolved_root.is_dir():
            raise ToolError("invalid_root", "Repository root must be a directory.")
        self._validate_integer(max_file_bytes, "max_file_bytes", minimum=1)
        self._validate_integer(max_read_lines, "max_read_lines", minimum=1)

        self.root = resolved_root
        self.max_file_bytes = max_file_bytes
        self.max_read_lines = max_read_lines
        self._git_path, self._git_executable = self._resolve_git_executable()
        self.schemas = copy.deepcopy(TOOL_SCHEMAS)
        self.tool_schemas = self.schemas
        self._files_read: set[str] = set()
        self._read_calls = 0
        self._context_chars = 0

    @property
    def files_read(self) -> list[str]:
        """Return canonical paths successfully requested through ``read_file``."""
        return sorted(self._files_read)

    @property
    def repo_summary(self) -> str:
        """Describe the tool boundary without exposing the host's absolute path."""
        return (
            f"Read-only repository named {self.root.name!r}. All tool paths and citations "
            "must be relative to its root."
        )

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "files_read": self.files_read,
            "read_calls": self._read_calls,
            "context_chars": self._context_chars,
        }

    def get_schemas(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self.schemas)

    def execute(self, name: str, arguments: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """Dispatch one allow-listed tool and turn expected failures into JSON-safe errors."""
        methods = {
            "git_diff": self.git_diff,
            "list_files": self.list_files,
            "read_file": self.read_file,
            "search_text": self.search_text,
        }
        if name not in methods:
            return {
                "error": ToolError("unknown_tool", f"Unknown read-only tool: {name!r}.").to_dict()
            }
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, Mapping):
            error = ToolError("invalid_arguments", "Tool arguments must be an object.")
            return {"error": error.to_dict()}
        try:
            return methods[name](**dict(arguments))
        except ToolError as exc:
            return {"error": exc.to_dict()}
        except TypeError:
            error = ToolError("invalid_arguments", f"Invalid arguments for tool {name!r}.")
            return {"error": error.to_dict()}

    def list_files(
        self,
        path: str = ".",
        pattern: str | None = None,
        limit: int = 200,
    ) -> dict[str, Any]:
        self._validate_integer(limit, "limit", minimum=1, maximum=MAX_LIST_LIMIT)
        normalized_pattern = self._validate_pattern(pattern)
        base_path, _ = self._resolve_path(path, must_exist=True)
        if not base_path.is_dir() and not base_path.is_file():
            raise ToolError("invalid_path", "The list path must be a file or directory.")

        files: list[str] = []
        blocked: defaultdict[str, int] = defaultdict(int)
        truncated = False
        scanned = 0
        for candidate in self._iter_candidates(base_path):
            scanned += 1
            if scanned > MAX_SCANNED_FILES:
                truncated = True
                break
            relative = candidate.relative_to(self.root).as_posix()
            if normalized_pattern and not fnmatch.fnmatchcase(relative, normalized_pattern):
                continue
            try:
                info = self._inspect_file(candidate)
            except ToolError as exc:
                blocked[self._blocked_category(exc)] += 1
                continue
            if len(files) >= limit:
                truncated = True
                break
            files.append(info.relative_path)

        return {
            "path": self._canonical_relative(path),
            "files": files,
            "count": len(files),
            "truncated": truncated,
            "blocked": dict(sorted(blocked.items())),
        }

    def search_text(
        self,
        query: str,
        path: str = ".",
        pattern: str | None = None,
        case_sensitive: bool = False,
        limit: int = 50,
    ) -> dict[str, Any]:
        if not isinstance(query, str) or not query or "\x00" in query:
            raise ToolError("invalid_query", "Search query must be a non-empty string.")
        if "\n" in query or "\r" in query or len(query) > 500:
            raise ToolError("invalid_query", "Search query must be one line and at most 500 chars.")
        if not isinstance(case_sensitive, bool):
            raise ToolError("invalid_arguments", "case_sensitive must be a boolean.")
        self._validate_integer(limit, "limit", minimum=1, maximum=MAX_SEARCH_LIMIT)
        normalized_pattern = self._validate_pattern(pattern)
        base_path, _ = self._resolve_path(path, must_exist=True)
        if not base_path.is_dir() and not base_path.is_file():
            raise ToolError("invalid_path", "The search path must be a file or directory.")

        needle = query if case_sensitive else query.casefold()
        matches: list[dict[str, Any]] = []
        evidence: list[dict[str, Any]] = []
        blocked: defaultdict[str, int] = defaultdict(int)
        truncated = False
        scanned = 0
        for candidate in self._iter_candidates(base_path):
            scanned += 1
            if scanned > MAX_SCANNED_FILES:
                truncated = True
                break
            relative = candidate.relative_to(self.root).as_posix()
            if normalized_pattern and not fnmatch.fnmatchcase(relative, normalized_pattern):
                continue
            try:
                info, text = self._read_safe_text(candidate)
            except ToolError as exc:
                blocked[self._blocked_category(exc)] += 1
                continue
            for line_number, line in enumerate(text.splitlines(), start=1):
                haystack = line if case_sensitive else line.casefold()
                if needle not in haystack:
                    continue
                if len(matches) >= limit:
                    truncated = True
                    break
                matches.append(
                    {
                        "path": info.relative_path,
                        "line": line_number,
                        "text": self._clip_line(line),
                        "citation": (
                            f"[{info.relative_path}:L{line_number}-L{line_number}]"
                        ),
                    }
                )
                evidence.append(self._line_evidence(info.relative_path, line_number, line))
            if truncated:
                break

        return {
            "query": query,
            "matches": matches,
            "count": len(matches),
            "truncated": truncated,
            "blocked": dict(sorted(blocked.items())),
            "_evidence": evidence,
        }

    def read_file(
        self,
        path: str,
        start_line: int = 1,
        end_line: int | None = None,
    ) -> dict[str, Any]:
        self._validate_integer(start_line, "start_line", minimum=1)
        if end_line is not None:
            self._validate_integer(end_line, "end_line", minimum=1)
            if end_line < start_line:
                raise ToolError("invalid_range", "end_line must not be before start_line.")
            if end_line - start_line + 1 > self.max_read_lines:
                raise ToolError(
                    "range_too_large",
                    f"A read may include at most {self.max_read_lines} lines.",
                )

        candidate, _ = self._resolve_path(path, must_exist=True)
        info, text = self._read_safe_text(candidate)
        lines = text.splitlines()
        total_lines = len(lines)
        if total_lines == 0:
            if start_line != 1:
                raise ToolError("invalid_range", "start_line is beyond the empty file.")
            actual_end = 0
            selected: list[str] = []
        else:
            if start_line > total_lines:
                raise ToolError(
                    "invalid_range",
                    f"start_line {start_line} is beyond the file's {total_lines} lines.",
                )
            requested_end = end_line or (start_line + self.max_read_lines - 1)
            actual_end = min(requested_end, total_lines)
            selected = lines[start_line - 1 : actual_end]

        content = "\n".join(
            f"L{line_number}: {line}"
            for line_number, line in enumerate(selected, start=start_line)
        )
        self._files_read.add(info.relative_path)
        self._read_calls += 1
        self._context_chars += len(content)
        return {
            "path": info.relative_path,
            "start_line": start_line,
            "end_line": actual_end,
            "total_lines": total_lines,
            "content": content,
            "truncated": actual_end < total_lines,
            "_evidence": [
                self._line_evidence(info.relative_path, line_number, line)
                for line_number, line in enumerate(selected, start=start_line)
            ],
        }

    def citation_snapshot(
        self,
        path: str,
        line_numbers: Iterable[int],
    ) -> dict[str, Any]:
        """Return current hashes for selected lines with one safe file read."""
        requested = sorted(set(line_numbers))
        if any(
            isinstance(line, bool) or not isinstance(line, int) or line < 1
            for line in requested
        ):
            raise ToolError("invalid_range", "Citation lines must be positive integers.")
        candidate, _ = self._resolve_path(path, must_exist=True)
        info, text = self._read_safe_text(candidate)
        lines = text.splitlines()
        return {
            "path": info.relative_path,
            "total_lines": len(lines),
            "_evidence": [
                self._line_evidence(info.relative_path, line, lines[line - 1])
                for line in requested
                if line <= len(lines)
            ],
        }

    def git_diff(
        self,
        base: str = "HEAD",
        path: str | None = None,
        staged: bool = False,
        context_lines: int = 3,
        max_chars: int = DEFAULT_MAX_DIFF_CHARS,
    ) -> dict[str, Any]:
        deadline = time.monotonic() + MAX_GIT_DIFF_SECONDS
        if not isinstance(staged, bool):
            raise ToolError("invalid_arguments", "staged must be a boolean.")
        self._validate_integer(context_lines, "context_lines", minimum=0, maximum=20)
        self._validate_integer(max_chars, "max_chars", minimum=1_000, maximum=200_000)
        revision = self._validate_revision(base)
        self._assert_git_root(deadline=deadline)
        self._git(
            ["rev-parse", "--verify", "--end-of-options", f"{revision}^{{commit}}"],
            deadline=deadline,
            max_output_bytes=4_096,
        )
        self._assert_no_git_filters(deadline=deadline)

        path_filter: str | None = None
        if path is not None:
            candidate, path_filter = self._resolve_path(path, must_exist=False)
            self._assert_not_sensitive(path_filter, candidate.resolve(strict=False))

        diff_prefix = [
            "diff",
            "--no-ext-diff",
            "--no-textconv",
            "--no-color",
            "--no-renames",
            f"--unified={context_lines}",
        ]
        if staged:
            diff_prefix.append("--cached")
        diff_prefix.append(revision)

        name_args = [*diff_prefix, "--name-only", "-z", "--"]
        if path_filter is not None:
            name_args.append(path_filter)
        raw_names = self._git(
            name_args,
            deadline=deadline,
            max_output_bytes=MAX_GIT_NAME_BYTES,
        )
        names_truncated = False
        try:
            changed_paths = [
                item.decode("utf-8") for item in raw_names.split(b"\x00") if item
            ]
        except UnicodeDecodeError as exc:
            raise ToolError("binary", "Git returned a non-UTF-8 path; diff was blocked.") from exc
        if len(changed_paths) > MAX_DIFF_PATHS:
            changed_paths = changed_paths[:MAX_DIFF_PATHS]
            names_truncated = True

        patches: list[str] = []
        included: list[str] = []
        blocked: defaultdict[str, int] = defaultdict(int)
        truncated = names_truncated
        used_chars = 0
        for changed_path in changed_paths:
            if time.monotonic() >= deadline:
                truncated = True
                break
            try:
                relative = self._validate_git_path(changed_path)
                lexical = self.root / relative
                self._assert_not_sensitive(relative, lexical.resolve(strict=False))
                if lexical.exists() or lexical.is_symlink():
                    self._inspect_file(lexical)
                if staged:
                    self._inspect_git_blob(f":{relative}", deadline=deadline)
                self._inspect_git_blob(f"{revision}:{relative}", deadline=deadline)
                raw_patch = self._git(
                    [*diff_prefix, "--", relative],
                    deadline=deadline,
                    max_output_bytes=max_chars,
                )
                patch = raw_patch.decode("utf-8")
            except UnicodeDecodeError:
                blocked["binary"] += 1
                continue
            except ToolError as exc:
                blocked[self._blocked_category(exc)] += 1
                continue
            if not patch:
                continue
            separator = "\n" if patches else ""
            remaining = max_chars - used_chars - len(separator)
            if remaining <= 0:
                truncated = True
                break
            patch_truncated = False
            if len(patch) > remaining:
                patch = self._truncate_text(patch, remaining)
                truncated = True
                patch_truncated = True
            patches.append(patch)
            included.append(relative)
            used_chars += len(separator) + len(patch)
            if patch_truncated:
                break

        return {
            "base": revision,
            "staged": staged,
            "files": included,
            "diff": "\n".join(patches),
            "truncated": truncated,
            "blocked": dict(sorted(blocked.items())),
        }

    def _resolve_path(self, raw_path: str, *, must_exist: bool) -> tuple[Path, str]:
        normalized = self._normalize_path(raw_path)
        lexical = self.root if normalized == "." else self.root / normalized
        try:
            resolved = lexical.resolve(strict=must_exist)
        except FileNotFoundError as exc:
            raise ToolError("not_found", f"Repository path not found: {normalized!r}.") from exc
        except (OSError, RuntimeError) as exc:
            message = f"Repository path is inaccessible: {normalized!r}."
            raise ToolError("unsafe_path", message) from exc
        if not self._is_within_root(resolved):
            raise ToolError("unsafe_path", "Path resolves outside the repository root.")
        return lexical, normalized

    def _normalize_path(self, raw_path: str) -> str:
        if not isinstance(raw_path, str):
            raise ToolError("invalid_path", "Repository path must be a string.")
        if not raw_path:
            return "."
        if "\x00" in raw_path or any(ord(char) < 32 for char in raw_path):
            raise ToolError("invalid_path", "Repository path contains control characters.")
        if "\\" in raw_path:
            raise ToolError("unsafe_path", "Backslashes are not allowed in repository paths.")
        pure = PurePosixPath(raw_path)
        if pure.is_absolute() or _WINDOWS_ABSOLUTE_PATH.match(raw_path):
            raise ToolError("unsafe_path", "Absolute repository paths are not allowed.")
        if ".." in pure.parts:
            raise ToolError("unsafe_path", "Parent traversal is not allowed in repository paths.")
        normalized = pure.as_posix()
        return "." if normalized in {"", "."} else normalized.removeprefix("./")

    def _canonical_relative(self, raw_path: str) -> str:
        return self._normalize_path(raw_path)

    def _is_within_root(self, path: Path) -> bool:
        return self._is_within(path, self.root)

    @staticmethod
    def _is_within(path: Path, boundary: Path) -> bool:
        try:
            path.relative_to(boundary)
        except ValueError:
            return False
        return True

    def _iter_candidates(self, base_path: Path) -> Iterator[Path]:
        if base_path.is_file() or base_path.is_symlink():
            yield base_path
            return
        for current_root, directory_names, file_names in os.walk(base_path, followlinks=False):
            current = Path(current_root)
            kept_directories: list[str] = []
            for name in sorted(directory_names):
                if name in _SKIPPED_DIRECTORIES or name.casefold().endswith(
                    _SKIPPED_DIRECTORY_SUFFIXES
                ):
                    continue
                candidate = current / name
                if candidate.is_symlink():
                    continue
                try:
                    if self._is_within_root(candidate.resolve(strict=True)):
                        kept_directories.append(name)
                except (OSError, RuntimeError):
                    continue
            directory_names[:] = kept_directories
            for name in sorted(file_names):
                yield current / name

    def _inspect_file(self, candidate: Path) -> _FileInfo:
        try:
            resolved = candidate.resolve(strict=True)
        except FileNotFoundError as exc:
            raise ToolError("not_found", "File no longer exists.") from exc
        except (OSError, RuntimeError) as exc:
            raise ToolError("unsafe_path", "File is inaccessible.") from exc
        if not self._is_within_root(resolved):
            raise ToolError("unsafe_path", "File resolves outside the repository root.")
        relative = candidate.relative_to(self.root).as_posix()
        self._assert_not_sensitive(relative, resolved)
        try:
            size, sample = self._read_descriptor(resolved, _BINARY_SAMPLE_BYTES)
        except OSError as exc:
            raise ToolError("unsafe_path", "File cannot be opened safely.") from exc
        if size > self.max_file_bytes:
            raise ToolError(
                "too_large",
                f"File exceeds the {self.max_file_bytes}-byte read limit.",
            )
        if self._looks_binary(sample, allow_trailing_partial=True):
            raise ToolError("binary", "Binary or non-UTF-8 files cannot be read.")
        return _FileInfo(resolved, relative, size)

    def _read_safe_text(self, candidate: Path) -> tuple[_FileInfo, str]:
        info = self._inspect_file(candidate)
        try:
            _, data = self._read_descriptor(info.path, self.max_file_bytes + 1)
        except OSError as exc:
            raise ToolError("unsafe_path", "File cannot be read.") from exc
        if len(data) > self.max_file_bytes:
            raise ToolError(
                "too_large",
                f"File exceeds the {self.max_file_bytes}-byte read limit.",
            )
        if self._looks_binary(data):
            raise ToolError("binary", "Binary or non-UTF-8 files cannot be read.")
        return info, data.decode("utf-8-sig")

    @staticmethod
    def _read_descriptor(path: Path, byte_limit: int) -> tuple[int, bytes]:
        flags = (
            os.O_RDONLY
            | getattr(os, "O_BINARY", 0)
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NONBLOCK", 0)
        )
        descriptor = os.open(path, flags)
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                raise OSError("not a regular file")
            with os.fdopen(descriptor, "rb", closefd=False) as handle:
                data = handle.read(byte_limit)
            return metadata.st_size, data
        finally:
            os.close(descriptor)

    def _assert_not_sensitive(self, relative: str, resolved: Path) -> None:
        resolved_relative = resolved.relative_to(self.root).as_posix()
        if self._is_sensitive(relative) or self._is_sensitive(resolved_relative):
            raise ToolError("sensitive", "Sensitive files are not available to repository tools.")

    @staticmethod
    def _is_sensitive(relative: str) -> bool:
        if any(
            relative == prefix or relative.startswith(f"{prefix}/")
            for prefix in (
                "examples/hy3-repo-scout/demos/artifacts",
                "examples/hy3-repo-scout/demos/media",
            )
        ):
            return True
        parts = [part.casefold() for part in PurePosixPath(relative).parts]
        if any(
            part in _BLOCKED_PATH_PARTS or part.endswith(_SKIPPED_DIRECTORY_SUFFIXES)
            for part in parts
        ):
            return True
        if not parts:
            return False
        name = parts[-1]
        if name == ".env" or (
            name.startswith(".env.") and name not in _SAFE_ENV_TEMPLATES
        ):
            return True
        if name in _SENSITIVE_NAMES:
            return True
        suffix = PurePosixPath(name).suffix.casefold()
        if suffix in _SENSITIVE_SUFFIXES:
            return True
        stem = PurePosixPath(name).stem.casefold()
        stem_tokens = set(re.split(r"[._-]+", stem))
        contains_api_key = re.search(r"(?:^|[._-])api[._-]?key(?:$|[._-])", stem)
        return suffix in _SENSITIVE_DATA_SUFFIXES and (
            bool(stem_tokens & _SENSITIVE_STEMS) or contains_api_key is not None
        )

    @staticmethod
    def _looks_binary(data: bytes, *, allow_trailing_partial: bool = False) -> bool:
        if not data:
            return False
        if b"\x00" in data:
            return True
        try:
            decoder = codecs.getincrementaldecoder("utf-8-sig")(errors="strict")
            decoder.decode(data, final=not allow_trailing_partial)
        except UnicodeDecodeError:
            return True
        control_count = sum(byte < 32 and byte not in b"\t\n\r\f\b" for byte in data)
        return control_count / len(data) > 0.05

    def _assert_git_root(self, *, deadline: float | None = None) -> None:
        raw_layout = self._git(
            [
                "rev-parse",
                "--show-toplevel",
                "--absolute-git-dir",
                "--git-common-dir",
                "--git-path",
                "objects",
                "--git-path",
                "index",
            ],
            deadline=deadline,
            max_output_bytes=16_384,
        )
        try:
            values = raw_layout.decode("utf-8").splitlines()
        except (UnicodeDecodeError, OSError, RuntimeError) as exc:
            raise ToolError("git_error", "Could not validate Git repository metadata.") from exc
        if len(values) != 5:
            raise ToolError("git_error", "Could not validate Git repository metadata.")

        top = self._resolve_git_metadata_path(values[0], must_exist=True)
        if top != self.root:
            raise ToolError("git_error", "git_diff requires the selected root to be the Git root.")
        git_dir = self._resolve_git_metadata_path(values[1], must_exist=True, allow_external=True)
        common_dir = self._resolve_git_metadata_path(
            values[2], must_exist=True, allow_external=True
        )
        objects_dir = self._resolve_git_metadata_path(
            values[3], must_exist=True, allow_external=True
        )
        index_path = self._resolve_git_metadata_path(
            values[4], must_exist=True, allow_external=True
        )

        metadata_paths = (git_dir, common_dir, objects_dir, index_path)
        if not all(self._is_within_root(path) for path in metadata_paths):
            self._assert_linked_worktree_layout(
                git_dir=git_dir,
                common_dir=common_dir,
                objects_dir=objects_dir,
                index_path=index_path,
            )
        for directory_name in ("info", "pack"):
            self._resolve_git_child(
                objects_dir / directory_name,
                boundary=objects_dir,
                must_exist=False,
            )
        for name in ("alternates", "http-alternates"):
            alternates = objects_dir / "info" / name
            self._resolve_git_child(alternates, boundary=objects_dir, must_exist=False)
            if alternates.exists() or alternates.is_symlink():
                raise ToolError("git_error", "Git object alternates are not available.")

    def _assert_linked_worktree_layout(
        self,
        *,
        git_dir: Path,
        common_dir: Path,
        objects_dir: Path,
        index_path: Path,
    ) -> None:
        selected_git = self.root / ".git"
        if selected_git.is_symlink() or not selected_git.is_file():
            raise ToolError("git_error", "External Git metadata is not available.")
        if git_dir.parent != common_dir / "worktrees":
            raise ToolError("git_error", "External Git metadata is not a linked worktree.")
        try:
            expected_objects = (common_dir / "objects").resolve(strict=True)
            expected_index = (git_dir / "index").resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise ToolError("git_error", "Could not validate linked-worktree metadata.") from exc
        if (
            objects_dir != expected_objects
            or index_path != expected_index
            or not self._is_within(objects_dir, common_dir)
            or not self._is_within(index_path, git_dir)
        ):
            raise ToolError("git_error", "Linked-worktree metadata layout is inconsistent.")

        selected_pointer = self._read_git_pointer(selected_git, prefix="gitdir:")
        admin_pointer = self._read_git_pointer(git_dir / "gitdir")
        common_pointer = self._read_git_pointer(git_dir / "commondir")
        if self._resolve_git_pointer(selected_pointer, self.root) != git_dir:
            raise ToolError("git_error", "Linked-worktree Git directory does not match.")
        if self._resolve_git_pointer(admin_pointer, git_dir) != selected_git.resolve(strict=True):
            raise ToolError("git_error", "Linked-worktree administrative backlink does not match.")
        if self._resolve_git_pointer(common_pointer, git_dir) != common_dir:
            raise ToolError("git_error", "Linked-worktree common directory does not match.")

    @classmethod
    def _read_git_pointer(cls, path: Path, *, prefix: str | None = None) -> str:
        if path.is_symlink():
            raise ToolError("git_error", "Linked-worktree metadata is malformed.")
        try:
            size, data = cls._read_descriptor(path, 4_097)
            text = data.decode("utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ToolError("git_error", "Could not validate linked-worktree metadata.") from exc
        lines = text.splitlines()
        if size > 4_096 or len(lines) != 1:
            raise ToolError("git_error", "Linked-worktree metadata is malformed.")
        value = lines[0].strip()
        if prefix is not None:
            marker = f"{prefix} "
            if not value.startswith(marker):
                raise ToolError("git_error", "Linked-worktree metadata is malformed.")
            value = value.removeprefix(marker).strip()
        if not value or "\x00" in value:
            raise ToolError("git_error", "Linked-worktree metadata is malformed.")
        return value

    @staticmethod
    def _resolve_git_pointer(value: str, base: Path) -> Path:
        path = Path(value)
        candidate = path if path.is_absolute() else base / path
        try:
            return candidate.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise ToolError("git_error", "Could not validate linked-worktree metadata.") from exc

    def _resolve_git_metadata_path(
        self,
        raw_path: str,
        *,
        must_exist: bool,
        allow_external: bool = False,
    ) -> Path:
        path = Path(raw_path)
        candidate = path if path.is_absolute() else self.root / path
        try:
            resolved = candidate.resolve(strict=must_exist)
        except (OSError, RuntimeError) as exc:
            raise ToolError("git_error", "Could not validate Git repository metadata.") from exc
        if not allow_external and not self._is_within_root(resolved):
            raise ToolError("git_error", "Git metadata resolves outside the repository root.")
        return resolved

    def _resolve_git_child(self, path: Path, *, boundary: Path, must_exist: bool) -> Path:
        try:
            resolved = path.resolve(strict=must_exist)
        except (OSError, RuntimeError) as exc:
            raise ToolError("git_error", "Could not validate Git repository metadata.") from exc
        if not self._is_within(resolved, boundary):
            raise ToolError("git_error", "Git metadata resolves outside its object store.")
        return resolved

    def _assert_no_git_filters(self, *, deadline: float | None = None) -> None:
        configured = self._git(
            ["config", "--null", "--get-regexp", r"^filter\."],
            deadline=deadline,
            max_output_bytes=4_096,
            allowed_returncodes=(0, 1),
        )
        if configured:
            raise ToolError(
                "git_filter",
                "git_diff is unavailable when repository filter drivers are configured.",
            )

    def _resolve_git_executable(self) -> tuple[str, str | None]:
        safe_directories: list[str] = []
        seen: set[str] = set()
        for entry in os.defpath.split(os.pathsep):
            if not entry or not os.path.isabs(entry):
                continue
            try:
                resolved = Path(entry).resolve(strict=True)
            except (OSError, RuntimeError):
                continue
            if not resolved.is_dir() or self._is_within_root(resolved):
                continue
            rendered = str(resolved)
            if rendered not in seen:
                seen.add(rendered)
                safe_directories.append(rendered)

        safe_path = os.pathsep.join(safe_directories)
        executable = shutil.which("git", path=safe_path) if safe_path else None
        if executable is None:
            return safe_path, None
        try:
            resolved_executable = Path(executable).resolve(strict=True)
        except (OSError, RuntimeError):
            return safe_path, None
        if self._is_within_root(resolved_executable):
            return safe_path, None
        return safe_path, str(resolved_executable)

    def _git(
        self,
        arguments: list[str],
        *,
        deadline: float | None = None,
        max_output_bytes: int = MAX_GIT_OUTPUT_BYTES,
        allowed_returncodes: tuple[int, ...] = (0,),
    ) -> bytes:
        environment = {
            name: os.environ[name]
            for name in ("SYSTEMROOT", "TMPDIR", "TEMP", "TMP", "LANG", "LC_ALL")
            if name in os.environ
        }
        environment.update(
            {
                "PATH": self._git_path,
                "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_CONFIG_SYSTEM": os.devnull,
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_ATTR_NOSYSTEM": "1",
                "GIT_LITERAL_PATHSPECS": "1",
                "GIT_NO_LAZY_FETCH": "1",
                "GIT_NO_REPLACE_OBJECTS": "1",
                "GIT_OPTIONAL_LOCKS": "0",
                "GIT_PAGER": "",
                "GIT_TERMINAL_PROMPT": "0",
            }
        )
        timeout = 10.0
        if deadline is not None:
            timeout = min(timeout, deadline - time.monotonic())
        if timeout <= 0:
            raise ToolError("git_timeout", "Git operation exceeded its total time limit.")
        if self._git_executable is None:
            raise ToolError("git_error", "A safe Git executable was not found.")
        popen_options: dict[str, Any] = {}
        if os.name == "posix":
            popen_options["start_new_session"] = True
        elif hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
            popen_options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        try:
            process = subprocess.Popen(
                [
                    self._git_executable,
                    "-c",
                    "core.fsmonitor=false",
                    "-c",
                    "core.hooksPath=/dev/null",
                    "-C",
                    str(self.root),
                    *arguments,
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=environment,
                **popen_options,
            )
        except OSError as exc:
            raise ToolError("git_error", "Git command could not be started.") from exc

        stdout_chunks: list[bytes] = []
        stdout_overflow = threading.Event()

        def terminate_process_tree() -> None:
            if os.name == "posix":
                with suppress(ProcessLookupError, PermissionError):
                    os.killpg(process.pid, signal.SIGKILL)
            elif process.poll() is None:
                with suppress(OSError):
                    process.kill()

        def drain(stream: Any, chunks: list[bytes], limit: int, stop_on_overflow: bool) -> None:
            used = 0
            while True:
                chunk = stream.read(65_536)
                if not chunk:
                    return
                available = max(0, limit - used)
                if available:
                    chunks.append(chunk[:available])
                    used += min(len(chunk), available)
                if len(chunk) > available and stop_on_overflow:
                    stdout_overflow.set()
                    terminate_process_tree()
                    return

        stdout_thread = threading.Thread(
            target=drain,
            args=(process.stdout, stdout_chunks, max_output_bytes, True),
            daemon=True,
        )
        stderr_thread = threading.Thread(
            target=drain,
            args=(process.stderr, [], 65_536, False),
            daemon=True,
        )
        stdout_thread.start()
        stderr_thread.start()
        timed_out = False
        try:
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                terminate_process_tree()
                process.wait()
        finally:
            if process.poll() is None:
                terminate_process_tree()
                process.wait()
            stdout_thread.join(timeout=0.5)
            stderr_thread.join(timeout=0.5)
            if stdout_thread.is_alive() or stderr_thread.is_alive():
                timed_out = True
                terminate_process_tree()
                for stream in (process.stdout, process.stderr):
                    if stream is not None:
                        with suppress(OSError):
                            os.close(stream.fileno())
                stdout_thread.join(timeout=0.5)
                stderr_thread.join(timeout=0.5)
            if process.stdout is not None:
                with suppress(OSError):
                    process.stdout.close()
            if process.stderr is not None:
                with suppress(OSError):
                    process.stderr.close()

        if stdout_overflow.is_set():
            raise ToolError("too_large", "Git output exceeded its safe byte limit.")
        if timed_out:
            raise ToolError("git_timeout", "Git operation exceeded its total time limit.")
        if process.returncode not in allowed_returncodes:
            raise ToolError("git_error", "Git command failed.")
        return b"".join(stdout_chunks)

    def _inspect_git_blob(self, object_name: str, *, deadline: float | None = None) -> None:
        try:
            raw_size = self._git(
                ["cat-file", "-s", object_name],
                deadline=deadline,
                max_output_bytes=128,
            )
        except ToolError as exc:
            if exc.code == "git_error":
                return
            raise
        try:
            size = int(raw_size.strip())
        except ValueError as exc:
            raise ToolError("git_error", "Git returned an invalid object size.") from exc
        if size > self.max_file_bytes:
            raise ToolError("too_large", "A changed Git object exceeds the file read limit.")
        data = self._git(
            ["cat-file", "blob", object_name],
            deadline=deadline,
            max_output_bytes=self.max_file_bytes + 1,
        )
        if self._looks_binary(data):
            raise ToolError("binary", "A changed Git object is binary or non-UTF-8.")

    def _validate_git_path(self, raw_path: str) -> str:
        normalized = self._normalize_path(raw_path)
        if normalized == ".":
            raise ToolError("unsafe_path", "Git returned an invalid empty path.")
        candidate = (self.root / normalized).resolve(strict=False)
        if not self._is_within_root(candidate):
            raise ToolError("unsafe_path", "Git returned a path outside the repository.")
        return normalized

    @staticmethod
    def _validate_revision(revision: str) -> str:
        if not isinstance(revision, str) or not _VALID_REVISION.fullmatch(revision):
            raise ToolError("invalid_revision", "Git base must be a simple commit or ref name.")
        if ".." in revision or len(revision) > 200:
            raise ToolError("invalid_revision", "Git revision ranges are not allowed.")
        return revision

    @staticmethod
    def _validate_pattern(pattern: str | None) -> str | None:
        if pattern is None:
            return None
        if not isinstance(pattern, str) or not pattern or len(pattern) > 300:
            raise ToolError("invalid_pattern", "File pattern must be a non-empty glob.")
        if "\x00" in pattern or "\\" in pattern or pattern.startswith("/"):
            raise ToolError("unsafe_path", "File pattern must be repository-relative.")
        if ".." in PurePosixPath(pattern).parts:
            raise ToolError("unsafe_path", "Parent traversal is not allowed in file patterns.")
        return pattern.removeprefix("./")

    @staticmethod
    def _validate_integer(
        value: int,
        name: str,
        *,
        minimum: int,
        maximum: int | None = None,
    ) -> None:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ToolError("invalid_arguments", f"{name} must be an integer.")
        if value < minimum or (maximum is not None and value > maximum):
            upper = f" and at most {maximum}" if maximum is not None else ""
            raise ToolError(
                "invalid_arguments",
                f"{name} must be at least {minimum}{upper}.",
            )

    @staticmethod
    def _blocked_category(error: ToolError) -> str:
        if error.code in {"binary", "sensitive", "too_large"}:
            return error.code
        return "unsafe"

    @staticmethod
    def _clip_line(line: str) -> str:
        if len(line) <= MAX_LINE_CHARS:
            return line
        return f"{line[: MAX_LINE_CHARS - 3]}..."

    @staticmethod
    def _line_evidence(path: str, line: int, content: str) -> dict[str, Any]:
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return {"path": path, "line": line, "sha256": digest}

    @staticmethod
    def _truncate_text(text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        if limit <= 3:
            return text[:limit]
        clipped = text[: limit - 3]
        newline = clipped.rfind("\n")
        if newline > 0:
            clipped = clipped[:newline]
        return f"{clipped}..."


__all__ = [
    "DEFAULT_MAX_FILE_BYTES",
    "RepoTools",
    "TOOL_SCHEMAS",
    "ToolError",
]
