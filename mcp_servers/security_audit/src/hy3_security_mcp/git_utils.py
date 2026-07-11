"""Git plumbing for the diff-review tool: read diffs and file text.

Shells out to the system `git` binary via subprocess — no GitPython
dependency. A non-zero exit becomes a GitError carrying git's own stderr, so
callers see the real reason (not a repo, bad ref range, ...) rather than a
generic failure.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

_TRUNCATION_SUFFIX = "\n…[截断 truncated]"

# Config keys whose values are arbitrary shell commands git executes during a
# diff of an untrusted repo. `filter.<name>.{clean,smudge,process}` run when a
# path is routed to the filter via .gitattributes; `diff.<name>.{command,
# textconv}` are external/textconv diff drivers; `core.fsmonitor` is a hook
# program run while refreshing the index. `<name>` is attacker-chosen, so these
# can't be pre-enumerated as static `-c` flags — the local config is read and
# each matching key is neutralized dynamically.
_EXEC_HOOK_KEY_RE = re.compile(
    r"^(?:filter\..*\.(?:clean|smudge|process)"
    r"|diff\..*\.(?:command|textconv)"
    r"|core\.fsmonitor)$"
)


def _exec_hook_overrides(repo_path: str, timeout: float) -> list[str]:
    """Return `-c <key>=` args neutralizing every exec hook in the repo's LOCAL
    config. Reading config with `git config --list` does NOT execute any filter,
    diff driver, or fsmonitor hook, so this is safe to run on an untrusted repo.
    A non-zero exit (e.g. not a repo) yields no overrides; the subsequent
    `git diff` surfaces that error instead.
    """
    result = subprocess.run(
        ["git", "-C", repo_path, "config", "--list", "--local", "-z"],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        return []
    overrides: list[str] = []
    for record in result.stdout.split("\0"):
        if not record:
            continue
        key = record.split("\n", 1)[0]  # `-z` record is `key\nvalue`
        if _EXEC_HOOK_KEY_RE.match(key):
            overrides.extend(["-c", f"{key}="])
    return overrides


# `review_diff` is meant to be pointed at UNTRUSTED repos, so a repo-local diff
# driver must never run: `git diff` honors `diff.external` / textconv drivers
# (arbitrary shell commands) configured in the target repo's own .git/config or
# the ambient GIT_EXTERNAL_DIFF env var — an RCE vector. Every diff is run with
# those disabled. The bound also stops a pathological/hung driver or huge repo
# from blocking forever.
_DEFAULT_TIMEOUT_SECONDS = 30.0


class GitError(Exception):
    """Raised when the underlying `git` invocation exits non-zero."""


def read_diff(
    repo_path: str = ".",
    *,
    staged: bool = False,
    ref_range: str | None = None,
    timeout: float = _DEFAULT_TIMEOUT_SECONDS,
) -> str:
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

    # -c diff.external= neutralizes a repo-local external diff driver and
    # -c core.fsmonitor= disables a repo-local fsmonitor hook; the per-command
    # --no-ext-diff / --no-textconv also disable external diff and textconv
    # drivers (belt-and-suspenders). GIT_EXTERNAL_DIFF is stripped from the
    # child env so an inherited value can't reintroduce the RCE.
    # `filter.<name>.*` / `diff.<name>.*` hooks use attacker-chosen names, so
    # they're neutralized dynamically from the repo's local config.
    env = {k: v for k, v in os.environ.items() if k != "GIT_EXTERNAL_DIFF"}

    try:
        overrides = _exec_hook_overrides(repo_path, timeout)
        args = [
            "git",
            "-C",
            repo_path,
            "-c",
            "diff.external=",
            "-c",
            "core.fsmonitor=",
            *overrides,
            "diff",
            "--no-ext-diff",
            "--no-textconv",
        ]
        if staged:
            args.append("--staged")
        if ref_range is not None:
            args.append(ref_range)

        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired as exc:
        raise GitError(f"git diff timed out after {timeout}s") from exc
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
