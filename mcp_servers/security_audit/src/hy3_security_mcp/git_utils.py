"""Git plumbing for the diff-review tool: read diffs and file text.

Shells out to the system `git` binary via subprocess — no GitPython
dependency. A non-zero exit becomes a GitError carrying git's own stderr, so
callers see the real reason (not a repo, bad ref range, ...) rather than a
generic failure.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

_TRUNCATION_SUFFIX = "\n…[截断 truncated]"


class GitError(Exception):
    """Raised when the underlying `git` invocation exits non-zero."""


def read_diff(repo_path: str = ".", *, staged: bool = False, ref_range: str | None = None) -> str:
    """Return `git diff` output for one repo ("" if there is no diff).

    `staged` and `ref_range` are mutually exclusive — diffing against the
    index and diffing between two refs are different git invocations — so
    combining them raises ValueError before any subprocess runs.

    A `ref_range` beginning with ``-`` is rejected with ValueError: git would
    otherwise interpret it as an option (argument smuggling, e.g.
    ``--output=<path>`` to write an arbitrary file), and no legitimate revision
    range starts with a dash.
    """
    if staged and ref_range is not None:
        raise ValueError("staged and ref_range are mutually exclusive")
    if ref_range is not None and ref_range.startswith("-"):
        raise ValueError(f"ref_range must not start with '-' (got {ref_range!r})")

    args = ["git", "-C", repo_path, "diff"]
    if staged:
        args.append("--staged")
    if ref_range is not None:
        args.append(ref_range)

    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise GitError(f"git diff failed (exit {result.returncode}): {result.stderr.strip()}")
    return result.stdout


def read_file_text(path: str, *, max_chars: int = 200_000) -> str:
    """Read a text file for review.

    A missing file raises FileNotFoundError, propagated as-is (fail fast —
    no swallowing). Content longer than `max_chars` is truncated with a
    trailing marker.
    """
    content = Path(path).read_text(encoding="utf-8")
    if len(content) > max_chars:
        return content[:max_chars] + _TRUNCATION_SUFFIX
    return content
