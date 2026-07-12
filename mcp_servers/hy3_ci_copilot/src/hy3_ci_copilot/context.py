from __future__ import annotations

import difflib
import os
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from hy3_ci_copilot.errors import AccessDeniedError, InputFileError
from hy3_ci_copilot.security import sanitize_untrusted_text, truncate_middle

_MANIFEST_NAMES = (
    "pyproject.toml",
    "package.json",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "Makefile",
    "requirements.txt",
    "uv.lock",
    "pnpm-lock.yaml",
    "yarn.lock",
    "package-lock.json",
)
_SIGNAL_WORDS = (
    "error",
    "failed",
    "failure",
    "fatal",
    "exception",
    "traceback",
    "panic",
    "timeout",
    "timed out",
    "denied",
    "not found",
    "warning",
)
_MAX_GIT_POINTER_BYTES = 4096
_MAX_GIT_CONFIG_BYTES = 1_000_000
_MAX_GIT_METADATA_ENTRIES = 50_000
_MAX_WORKFLOW_ALIASES = 100


def _contains_git_metadata_part(path: Path) -> bool:
    return any(part.rstrip(" .").casefold() == ".git" for part in path.parts)


@dataclass(frozen=True, slots=True)
class FileExcerpt:
    relative_path: str
    content: str
    original_bytes: int
    truncated: bool


class PathPolicy:
    def __init__(self, allowed_roots: tuple[Path, ...]) -> None:
        self.allowed_roots = tuple(root.resolve() for root in allowed_roots)

    def repository(self, value: str) -> Path:
        requested = Path(value).expanduser()
        if _contains_git_metadata_part(requested):
            raise AccessDeniedError("Using .git as repository_path is not allowed.")
        path = requested.resolve()
        if not path.is_dir():
            raise InputFileError(f"Repository directory does not exist: {value}")
        if _contains_git_metadata_part(path):
            raise AccessDeniedError("Using .git as repository_path is not allowed.")
        if not any(path.is_relative_to(root) for root in self.allowed_roots):
            raise AccessDeniedError("Repository is outside HY3_ALLOWED_ROOTS.")
        return path

    def file(self, value: str, repository: Path) -> Path:
        candidate = Path(value).expanduser()
        requested = candidate if candidate.is_absolute() else repository / candidate
        if _contains_git_metadata_part(requested):
            raise AccessDeniedError("Reading files inside .git is not allowed.")
        path = requested.resolve()
        if not path.is_relative_to(repository):
            raise AccessDeniedError("Input files must stay inside repository_path.")
        if _contains_git_metadata_part(path):
            raise AccessDeniedError("Reading files inside .git is not allowed.")
        if not any(path.is_relative_to(root) for root in self.allowed_roots):
            raise AccessDeniedError("Input file is outside HY3_ALLOWED_ROOTS.")
        if not path.exists():
            raise InputFileError(f"Input file does not exist: {value}")
        if not stat.S_ISREG(path.stat().st_mode):
            raise InputFileError(f"Input must be a regular file: {value}")
        return path


def read_text_excerpt(path: Path, repository: Path, max_chars: int) -> FileExcerpt:
    size = path.stat().st_size
    if size == 0:
        raise InputFileError(f"Input file is empty: {path.relative_to(repository)}")
    max_bytes = max(64_000, max_chars * 4)
    with path.open("rb") as handle:
        if size <= max_bytes:
            raw = handle.read()
            byte_truncated = False
        else:
            head_size = int(max_bytes * 0.4)
            tail_size = max_bytes - head_size
            head = handle.read(head_size)
            handle.seek(-tail_size, 2)
            tail = handle.read(tail_size)
            raw = head + b"\n\n... [byte range omitted] ...\n\n" + tail
            byte_truncated = True
    if b"\x00" in raw:
        raise InputFileError(f"Binary files are not supported: {path.relative_to(repository)}")
    clean = sanitize_untrusted_text(raw.decode("utf-8", errors="replace"))
    content = truncate_middle(clean, max_chars, path.name)
    return FileExcerpt(
        relative_path=sanitize_untrusted_text(str(path.relative_to(repository))),
        content=content,
        original_bytes=size,
        truncated=byte_truncated or len(clean) > max_chars,
    )


def _git_environment(repository: Path) -> dict[str, str]:
    inherited_names = ("PATH", "SYSTEMROOT", "WINDIR", "PATHEXT", "TMPDIR", "TEMP", "TMP")
    env = {name: os.environ[name] for name in inherited_names if name in os.environ}
    env.update(
        {
            "GIT_ATTR_NOSYSTEM": "1",
            "GIT_CEILING_DIRECTORIES": str(repository.parent),
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_DISCOVERY_ACROSS_FILESYSTEM": "0",
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_PAGER": "cat",
            "GIT_TERMINAL_PROMPT": "0",
            "PAGER": "cat",
        }
    )
    return env


def _run_git(
    repository: Path,
    git_directory: Path,
    *args: str,
    max_chars: int = 4000,
) -> str:
    try:
        result = subprocess.run(
            [
                "git",
                "--no-pager",
                "--git-dir",
                str(git_directory),
                "--work-tree",
                str(repository),
                "-c",
                "core.fsmonitor=false",
                "-c",
                "core.untrackedCache=false",
                "-c",
                "credential.helper=",
                *args,
            ],
            check=False,
            capture_output=True,
            encoding="utf-8",
            env=_git_environment(repository),
            errors="replace",
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unavailable"
    output = result.stdout.strip() if result.returncode == 0 else "unavailable"
    return truncate_middle(sanitize_untrusted_text(output), max_chars, "git output")


def _resolve_allowed_directory(
    candidate: Path,
    allowed_roots: tuple[Path, ...],
) -> Path | None:
    absolute = Path(os.path.abspath(candidate))
    for root in allowed_roots:
        try:
            relative = absolute.relative_to(root)
        except ValueError:
            continue
        current = root
        try:
            root_stat = current.lstat()
            if stat.S_ISLNK(root_stat.st_mode) or not stat.S_ISDIR(root_stat.st_mode):
                continue
            for part in relative.parts:
                current /= part
                current_stat = current.lstat()
                if stat.S_ISLNK(current_stat.st_mode):
                    break
            else:
                if stat.S_ISDIR(current_stat.st_mode if relative.parts else root_stat.st_mode):
                    return absolute
        except OSError:
            continue
    return None


def _read_git_pointer(path: Path, prefix: str = "") -> str | None:
    try:
        path_stat = path.lstat()
        if (
            stat.S_ISLNK(path_stat.st_mode)
            or not stat.S_ISREG(path_stat.st_mode)
            or path_stat.st_size > _MAX_GIT_POINTER_BYTES
        ):
            return None
        lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
    except (OSError, UnicodeError):
        return None
    if len(lines) != 1:
        return None
    value = lines[0]
    if prefix:
        if not value.lower().startswith(prefix):
            return None
        value = value[len(prefix) :]
    value = value.strip()
    return value if value and "\x00" not in value else None


def _resolve_common_git_directory(
    git_directory: Path,
    allowed_roots: tuple[Path, ...],
) -> Path | None:
    pointer = git_directory / "commondir"
    if not pointer.exists():
        return git_directory
    raw_target = _read_git_pointer(pointer)
    if raw_target is None:
        return None
    target = Path(raw_target)
    requested = target if target.is_absolute() else git_directory / target
    return _resolve_allowed_directory(requested, allowed_roots)


def _git_metadata_is_safe(directories: tuple[Path, ...]) -> bool:
    roots: list[Path] = []
    for directory in sorted(set(directories), key=lambda item: len(item.parts)):
        if not any(directory.is_relative_to(root) for root in roots):
            roots.append(directory)

    seen = 0
    pending = list(roots)
    while pending:
        current = pending.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    seen += 1
                    if seen > _MAX_GIT_METADATA_ENTRIES:
                        return False
                    entry_stat = entry.stat(follow_symlinks=False)
                    if stat.S_ISLNK(entry_stat.st_mode):
                        return False
                    if stat.S_ISDIR(entry_stat.st_mode):
                        pending.append(Path(entry.path))
                    elif not stat.S_ISREG(entry_stat.st_mode):
                        return False
        except OSError:
            return False
    return True


def _git_config_is_safe(path: Path, repository: Path) -> bool:
    if not path.exists():
        return True
    try:
        path_stat = path.lstat()
        if not stat.S_ISREG(path_stat.st_mode) or path_stat.st_size > _MAX_GIT_CONFIG_BYTES:
            return False
        result = subprocess.run(
            [
                "git",
                "--no-pager",
                "config",
                "--file",
                str(path),
                "--no-includes",
                "--name-only",
                "--null",
                "--list",
            ],
            check=False,
            capture_output=True,
            encoding="utf-8",
            env=_git_environment(repository),
            errors="replace",
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    if result.returncode != 0:
        return False
    keys = (key.casefold() for key in result.stdout.split("\x00") if key)
    return not any(
        key == "include.path"
        or key.startswith("includeif.")
        or key in {"core.alternaterefscommand", "extensions.refstorage", "mailmap.file"}
        for key in keys
    )


def _git_storage_is_safe(
    repository: Path,
    git_directory: Path,
    common_directory: Path,
) -> bool:
    for name in ("alternates", "http-alternates"):
        if (common_directory / "objects" / "info" / name).exists():
            return False
    return all(
        _git_config_is_safe(path, repository)
        for path in (common_directory / "config", git_directory / "config.worktree")
    )


def _resolve_git_directory(
    repository: Path,
    allowed_roots: tuple[Path, ...],
) -> Path | None:
    roots = tuple(root.resolve() for root in allowed_roots)
    marker = repository / ".git"
    if marker.is_symlink():
        return None
    if marker.is_dir():
        resolved = _resolve_allowed_directory(marker, roots)
    elif marker.is_file():
        raw_target = _read_git_pointer(marker, "gitdir:")
        if raw_target is None:
            return None
        target = Path(raw_target)
        requested = target if target.is_absolute() else marker.parent / target
        resolved = _resolve_allowed_directory(requested, roots)
    else:
        return None
    if resolved is None:
        return None
    common = _resolve_common_git_directory(resolved, roots)
    if common is None:
        return None
    if not _git_metadata_is_safe((resolved, common)):
        return None
    if not _git_storage_is_safe(repository, resolved, common):
        return None
    return resolved


def git_context(
    repository: Path,
    max_chars: int = 6000,
    allowed_roots: tuple[Path, ...] | None = None,
) -> dict[str, str]:
    roots = allowed_roots or (repository,)
    git_directory = _resolve_git_directory(repository, roots)
    if git_directory is None:
        return {"branch": "unavailable", "status": "unavailable", "recent_commits": "unavailable"}
    per_field = max(100, max_chars // 3)
    result = {
        "branch": _run_git(
            repository,
            git_directory,
            "branch",
            "--show-current",
            max_chars=per_field,
        ),
        "status": "unavailable",
        "recent_commits": _run_git(
            repository,
            git_directory,
            "log",
            "--no-show-signature",
            "-5",
            "--pretty=format:%h %s",
            max_chars=per_field,
        ),
    }
    return {key: truncate_middle(value, per_field, f"git {key}") for key, value in result.items()}


def _candidate_context_files(repository: Path) -> list[Path]:
    files: list[Path] = []
    workflow_dir = repository / ".github" / "workflows"
    if workflow_dir.is_dir():
        files.extend(sorted(workflow_dir.glob("*.yml")))
        files.extend(sorted(workflow_dir.glob("*.yaml")))
    for name in _MANIFEST_NAMES:
        path = repository / name
        if path.is_file():
            files.append(path)
    files.extend(sorted(repository.glob("requirements*.txt")))
    return list(dict.fromkeys(files))


def repository_context(
    repository: Path,
    max_chars: int,
    allowed_roots: tuple[Path, ...] | None = None,
) -> dict[str, Any]:
    total_budget = max(2000, max_chars)
    git_budget = min(6000, max(300, total_budget // 5))
    budget = total_budget - git_budget
    files: list[dict[str, Any]] = []
    candidates = _candidate_context_files(repository)[:24]
    per_file = max(1000, min(12_000, budget // max(1, len(candidates))))
    for path in candidates:
        if budget <= 0:
            break
        if path.is_symlink():
            continue
        absolute = path.absolute()
        resolved = path.resolve()
        if (
            resolved != absolute
            or not resolved.is_relative_to(repository)
            or _contains_git_metadata_part(resolved)
            or not resolved.is_file()
        ):
            continue
        try:
            excerpt = read_text_excerpt(resolved, repository, min(per_file, budget))
        except (InputFileError, OSError):
            continue
        files.append(
            {
                "path": excerpt.relative_path,
                "content": excerpt.content,
                "truncated": excerpt.truncated,
            }
        )
        budget -= len(excerpt.content)
    return {
        "git": git_context(repository, git_budget, allowed_roots),
        "files": files,
    }


def parse_workflow(content: str) -> dict[str, Any]:
    try:
        depth = 0
        aliases = 0
        for event_count, event in enumerate(yaml.parse(content, Loader=yaml.BaseLoader), start=1):
            if event_count > 10_000:
                raise InputFileError("Workflow YAML is too complex.")
            if isinstance(event, yaml.events.AliasEvent):
                aliases += 1
                if aliases > _MAX_WORKFLOW_ALIASES:
                    raise InputFileError("Workflow YAML contains too many aliases.")
            if isinstance(event, (yaml.events.MappingStartEvent, yaml.events.SequenceStartEvent)):
                depth += 1
                if depth > 100:
                    raise InputFileError("Workflow YAML nesting is too deep.")
            elif isinstance(event, (yaml.events.MappingEndEvent, yaml.events.SequenceEndEvent)):
                depth -= 1
        document = yaml.load(content, Loader=yaml.BaseLoader)
    except yaml.YAMLError as exc:
        raise InputFileError(f"Workflow is not valid YAML: {exc}") from exc
    if not isinstance(document, dict):
        raise InputFileError("Workflow YAML must contain a mapping at the top level.")
    jobs = document.get("jobs", {})
    job_names = sorted(str(name) for name in jobs) if isinstance(jobs, dict) else []
    return {"top_level_keys": sorted(str(key) for key in document), "jobs": job_names}


def signal_lines(text: str, max_lines: int = 240) -> list[str]:
    signals = [
        line.strip()
        for line in text.splitlines()
        if any(word in line.lower() for word in _SIGNAL_WORDS)
    ]
    if len(signals) <= max_lines:
        return signals
    keep_head = max_lines // 3
    return [
        *signals[:keep_head],
        "... signal lines omitted ...",
        *signals[-(max_lines - keep_head) :],
    ]


def signal_diff(successful_log: str, failed_log: str, max_chars: int = 24_000) -> str:
    lines = difflib.unified_diff(
        signal_lines(successful_log),
        signal_lines(failed_log),
        fromfile="successful-run-signals",
        tofile="failed-run-signals",
        lineterm="",
        n=1,
    )
    return truncate_middle("\n".join(lines), max_chars, "signal diff")
