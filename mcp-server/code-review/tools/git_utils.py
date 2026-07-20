"""
Git 命令封装 — 所有与 git 交互的操作集中在这里。

职责:
  - 获取变更文件列表 (git diff --name-status)
  - 获取文件在某个 ref 的内容 (git show <ref>:<path>)
  - 获取单个文件的 diff (git diff <base> -- <path>)
  - 读取工作区文件

外部只需要调这几个函数，不需要直接跑 git 命令。
"""

import subprocess
import os
from typing import Optional


def get_changed_files(
    project_root: str,
    base_branch: str = "main",
) -> list[tuple[str, str, Optional[str]]]:
    """获取变更文件列表及其变更类型。

    当 base_branch="HEAD" 时，使用 git status --porcelain 以包含 untracked 文件。
    当 base_branch 为其他值时，使用 git diff --name-status <base_branch>。

    Args:
        project_root: 项目根目录
        base_branch: 对比的基准分支/commit，默认 HEAD

    Returns:
        [(path, change_type, old_path_or_None), ...]
        change_type 是单字符: 'M' | 'A' | 'D' | 'R'
        只有 'R' (rename) 时 old_path 才有值
    """
    if base_branch == "HEAD":
        return _get_changed_porcelain(project_root)
    else:
        return _get_changed_diff(project_root, base_branch)


def _get_changed_porcelain(project_root: str) -> list[tuple[str, str, Optional[str]]]:
    """通过 git status --porcelain 获取所有变更（含 untracked 源文件）。"""
    code, stdout, _ = _run_git(
        ["status", "--porcelain", "-u"],
        project_root,
    )
    if code != 0 or not stdout.strip():
        return []

    results = []
    for line in stdout.split("\n"):
        line = line.rstrip("\r\n")
        if not line or len(line) < 3:
            continue

        xy = line[:2]       # " M", "??", "A ", "R "
        rest = line[3:]     # file path (or "old -> new" for renames)

        # ── Rename ──
        if xy[0] == "R" or xy[1] == "R":
            # "R  old -> new"
            if " -> " in rest:
                old, new = rest.split(" -> ", 1)
                results.append((new.strip(), "R", old.strip()))
            else:
                results.append((rest, "R", None))
            continue

        # ── Untracked ──
        if xy == "??":
            results.append((rest, "A", None))  # untracked → treat as added
            continue

        # ── Deleted ──
        if "D" in xy:
            results.append((rest, "D", None))
            continue

        # ── Added (staged) ──
        if xy[0] == "A":
            results.append((rest, "A", None))
            continue

        # ── Modified (staged or unstaged) ──
        if "M" in xy:
            results.append((rest, "M", None))
            continue

        # ── Copied ──
        if "C" in xy:
            if " -> " in rest:
                old, new = rest.split(" -> ", 1)
                results.append((new.strip(), "A", old.strip()))
            else:
                results.append((rest, "A", None))

    return results


def _get_changed_diff(
    project_root: str,
    base_branch: str,
) -> list[tuple[str, str, Optional[str]]]:
    """通过 git diff --name-status 获取相对于指定分支的变更。"""
    code, stdout, _ = _run_git(
        ["diff", "--name-status", "--diff-filter=MARC", base_branch],
        project_root,
    )
    if code != 0 or not stdout.strip():
        return []

    results = []
    for line in stdout.split("\n"):
        line = line.rstrip("\r\n")
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue

        raw_type = parts[0]        # "M", "A", "D", "R100"
        change_type = raw_type[0]  # 取首字符

        if change_type == "R" and len(parts) >= 3:
            results.append((parts[2], "R", parts[1]))
        else:
            results.append((parts[1], change_type, None))

    return results


def get_file_at_ref(
    project_root: str,
    file_path: str,
    ref: str = "HEAD",
) -> Optional[str]:
    """获取文件在指定 git ref 的完整内容。

    等价命令: git show <ref>:<file_path>

    用于: 获取基准分支上的文件版本（而非工作区版本）
    """
    code, stdout, _ = _run_git(
        ["show", f"{ref}:{file_path}"],
        project_root,
    )
    return stdout if code == 0 else None


def get_file_diff(
    project_root: str,
    file_path: str,
    base_branch: str = "HEAD",
) -> str:
    """获取单个文件相对于基准分支的 diff。

    等价命令: git diff <base_branch> -- <file_path>

    只返回 hunk 部分，不含完整文件。用于行标注。
    """
    code, stdout, _ = _run_git(
        ["diff", base_branch, "--", file_path],
        project_root,
    )
    return stdout if code == 0 else ""


def read_working_file(project_root: str, file_path: str) -> Optional[str]:
    """从工作区读取文件内容。"""
    full = os.path.join(project_root, file_path)
    try:
        with open(full, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except (OSError, PermissionError):
        return None


def _run_git(args: list[str], cwd: str) -> tuple[int, str, str]:
    """执行 git 命令，返回 (returncode, stdout, stderr)。"""
    try:
        p = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError:
        return -1, "", "git not found"
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
