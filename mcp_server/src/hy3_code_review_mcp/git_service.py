"""Safe, read-only Git diff collection."""

from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

DiffSource = Literal["working_tree", "staged", "refs", "provided"]

_SENSITIVE_NAMES = {
    ".env",
    ".npmrc",
    ".pypirc",
    "credentials",
    "credentials.json",
    "id_dsa",
    "id_ed25519",
    "id_rsa",
}
_SENSITIVE_SUFFIXES = {".key", ".p12", ".pfx", ".pem"}


class GitServiceError(ValueError):
    """Raised when a diff cannot be collected safely."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "GIT_DIFF_ERROR",
        suggested_action: str = (
            "Check the repository, diff source, and Git references, then retry."
        ),
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.suggested_action = suggested_action
        self.retryable = retryable


@dataclass(frozen=True, slots=True)
class DiffPayload:
    """A collected diff and metadata relevant to model prompting."""

    content: str
    source: DiffSource
    repository: str | None
    truncated: bool = False
    original_chars: int = 0


class GitService:
    """Collect Git diffs while restricting access to a configured workspace."""

    def __init__(self, workspace_root: Path, max_diff_chars: int) -> None:
        self.workspace_root = workspace_root.resolve()
        self.max_diff_chars = max_diff_chars

    def collect_diff(
        self,
        *,
        repository_path: str = ".",
        source: DiffSource = "working_tree",
        base_ref: str | None = None,
        target_ref: str | None = None,
        provided_diff: str | None = None,
    ) -> DiffPayload:
        """Collect a diff from a supported source and enforce the size limit."""
        if source == "provided":
            if not provided_diff or not provided_diff.strip():
                raise GitServiceError(
                    "provided_diff is required when source='provided'",
                    code="INVALID_DIFF_INPUT",
                    suggested_action="Pass a non-empty unified diff in provided_diff.",
                )
            return self._limit(
                self._omit_sensitive_files(provided_diff),
                source=source,
                repository=None,
            )

        repository = self._resolve_repository(repository_path)
        command = [
            "git",
            "-C",
            str(repository),
            "diff",
            "--no-ext-diff",
            "--no-textconv",
        ]

        if source == "working_tree":
            command.append("--")
        elif source == "staged":
            command.extend(["--cached", "--"])
        elif source == "refs":
            if not base_ref:
                raise GitServiceError(
                    "base_ref is required when source='refs'",
                    code="INVALID_DIFF_INPUT",
                    suggested_action="Pass a valid base_ref, and optionally target_ref.",
                )
            self._validate_ref(base_ref, "base_ref")
            command.append(base_ref)
            if target_ref:
                self._validate_ref(target_ref, "target_ref")
                command.append(target_ref)
            command.append("--")
        else:
            raise GitServiceError(
                f"unsupported diff source: {source}",
                code="INVALID_DIFF_INPUT",
                suggested_action="Use working_tree, staged, refs, or provided.",
            )

        completed = self._run_git(command, timeout=30, operation="git diff")
        if completed.returncode != 0:
            detail = completed.stderr.strip() or "git diff failed"
            raise GitServiceError(
                detail,
                code="GIT_DIFF_FAILED",
                suggested_action=(
                    "Check that the selected Git references exist and the repository is readable."
                ),
            )
        if not completed.stdout.strip():
            raise GitServiceError(
                "the selected diff is empty",
                code="EMPTY_DIFF",
                suggested_action="Choose a diff source that currently contains changes.",
            )

        return self._limit(
            self._omit_sensitive_files(completed.stdout),
            source=source,
            repository=str(repository),
        )

    def _resolve_repository(self, repository_path: str) -> Path:
        candidate = Path(repository_path).expanduser()
        if not candidate.is_absolute():
            candidate = self.workspace_root / candidate
        candidate = candidate.resolve()

        if not candidate.is_relative_to(self.workspace_root):
            raise GitServiceError(
                "repository_path must stay inside HY3_WORKSPACE_ROOT",
                code="WORKSPACE_ACCESS_DENIED",
                suggested_action="Pass a repository inside the configured HY3_WORKSPACE_ROOT.",
            )
        if not candidate.is_dir():
            raise GitServiceError(
                f"repository_path is not a directory: {candidate}",
                code="INVALID_REPOSITORY",
                suggested_action="Pass the path of an existing Git working tree.",
            )

        check = self._run_git(
            ["git", "-C", str(candidate), "rev-parse", "--is-inside-work-tree"],
            timeout=10,
            operation="git rev-parse",
        )
        if check.returncode != 0 or check.stdout.strip() != "true":
            raise GitServiceError(
                f"repository_path is not a Git work tree: {candidate}",
                code="INVALID_REPOSITORY",
                suggested_action="Pass a directory inside an initialized Git working tree.",
            )
        return candidate

    @staticmethod
    def _validate_ref(value: str, name: str) -> None:
        if not value or value.startswith("-") or "\x00" in value or "\n" in value or "\r" in value:
            raise GitServiceError(
                f"{name} is not a safe Git reference",
                code="INVALID_GIT_REF",
                suggested_action=(
                    "Pass a commit, branch, or tag name without option prefixes or control "
                    "characters."
                ),
            )
        if len(value) > 256:
            raise GitServiceError(
                f"{name} is too long",
                code="INVALID_GIT_REF",
                suggested_action="Pass a Git reference no longer than 256 characters.",
            )

    @staticmethod
    def _run_git(
        command: list[str],
        *,
        timeout: int,
        operation: str,
    ) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise GitServiceError(
                f"{operation} timed out",
                code="GIT_TIMEOUT",
                suggested_action="Retry once or reduce the repository/diff scope.",
                retryable=True,
            ) from exc
        except OSError as exc:
            raise GitServiceError(
                f"could not execute {operation}",
                code="GIT_UNAVAILABLE",
                suggested_action="Confirm that Git is installed and executable by the MCP server.",
            ) from exc

    def _limit(
        self,
        content: str,
        *,
        source: DiffSource,
        repository: str | None,
    ) -> DiffPayload:
        original_chars = len(content)
        if original_chars <= self.max_diff_chars:
            return DiffPayload(
                content=content,
                source=source,
                repository=repository,
                original_chars=original_chars,
            )

        marker = (
            "\n\n[DIFF TRUNCATED BY SERVER: "
            f"showing {self.max_diff_chars} of {original_chars} characters]\n"
        )
        return DiffPayload(
            content=content[: self.max_diff_chars] + marker,
            source=source,
            repository=repository,
            truncated=True,
            original_chars=original_chars,
        )

    @classmethod
    def _omit_sensitive_files(cls, diff: str) -> str:
        """Remove complete unified-diff sections for common credential files."""
        lines = diff.splitlines(keepends=True)
        output: list[str] = []
        section: list[str] = []
        omitted_path: str | None = None

        def flush() -> None:
            nonlocal section, omitted_path
            if not section:
                return
            if omitted_path:
                output.append(f"[SENSITIVE FILE DIFF OMITTED: {omitted_path}]\n")
            else:
                output.extend(section)
            section = []
            omitted_path = None

        for line in lines:
            if line.startswith("diff --git "):
                flush()
                section = [line]
                paths = cls._parse_diff_header(line)
                sensitive = next((path for path in paths if cls._is_sensitive_path(path)), None)
                omitted_path = sensitive
            elif section:
                section.append(line)
            else:
                output.append(line)
        flush()
        return "".join(output)

    @staticmethod
    def _parse_diff_header(header: str) -> tuple[str, ...]:
        try:
            parts = shlex.split(header.strip())
        except ValueError:
            return ()
        if len(parts) < 4:
            return ()
        return tuple(part[2:] if part.startswith(("a/", "b/")) else part for part in parts[2:4])

    @staticmethod
    def _is_sensitive_path(value: str) -> bool:
        path = Path(value)
        name = path.name.lower()
        return (
            name in _SENSITIVE_NAMES
            or name.startswith(".env.")
            or path.suffix.lower() in _SENSITIVE_SUFFIXES
        )
