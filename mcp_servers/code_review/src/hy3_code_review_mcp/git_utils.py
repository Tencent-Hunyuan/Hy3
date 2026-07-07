from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional


def truncate_text(text: str, max_chars: int) -> str:
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}\n\n[truncated: original {len(text)} chars]"


def get_git_diff(
    repo_path: str,
    base_ref: str = "HEAD",
    target_ref: Optional[str] = None,
    max_chars: int = 24000,
) -> str:
    repo = Path(repo_path).expanduser().resolve()
    if not repo.exists() or not repo.is_dir():
        raise ValueError(f"repo_path must be an existing directory: {repo}")

    command = ["git", "diff", base_ref]
    if target_ref:
        command.append(target_ref)
    command.append("--")

    result = subprocess.run(
        command,
        cwd=repo,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git diff failed")

    diff = result.stdout.strip()
    if not diff:
        return "No diff found for the requested refs/worktree."
    return truncate_text(diff, max_chars=max_chars)
