"""
内容组装器 — 生成项目目录树 + 格式化标注文件。

输出供 Hy3 评审使用。
"""

import os
from tools.types import AnnotatedLine

def generate_project_tree(
    project_root: str,
    changed_labels: dict[str, str],
) -> str:
    """生成完整的项目目录树（递归到叶子节点，不截断，不过滤）。"""
    lines = [os.path.basename(project_root.rstrip("/\\")) + "/"]

    def _walk(dir_path: str, prefix: str):
        try:
            entries = sorted(os.listdir(dir_path))
        except (PermissionError, OSError):
            return

        # 只跳过 .git（元数据目录，不是项目源码）
        entries = [e for e in entries if e != ".git"]
        dirs = [e for e in entries if os.path.isdir(os.path.join(dir_path, e))]
        files = [e for e in entries if os.path.isfile(os.path.join(dir_path, e))]

        total = len(dirs) + len(files)
        for i, name in enumerate(dirs + files):
            is_last = (i == total - 1)
            full = os.path.join(dir_path, name)
            rel = os.path.relpath(full, project_root).replace("\\", "/")
            is_dir = os.path.isdir(full)

            connector = "└── " if is_last else "├── "
            display = name + ("/" if is_dir else "")
            label = changed_labels.get(rel, "")
            lines.append(prefix + connector + display + label)

            if is_dir:
                ext_prefix = "    " if is_last else "│   "
                _walk(full, prefix + ext_prefix)

    _walk(project_root, "")
    return "\n".join(lines)


def format_annotated_file(annotated_lines: list[AnnotatedLine]) -> str:
    """将标注行列表格式化为可读文本。

    输出示例:
        1| import { a } from './x';
        2| import { b } from './y';  // [ADDED]
        5|   return a() + b();       // [MODIFIED] 原:   return a();
    """
    if not annotated_lines:
        return ""

    max_line = max((a.line_number for a in annotated_lines), default=1)
    num_width = max(len(str(max_line)), 3)

    parts = []
    for a in annotated_lines:
        ln = str(a.line_number).rjust(num_width)
        if a.annotation == "UNCHANGED":
            parts.append(f" {ln}| {a.content}")
        elif a.annotation == "ADDED":
            parts.append(f" {ln}| {a.content}  // [ADDED]")
        elif a.annotation == "MODIFIED":
            old = a.old_content or "(unknown)"
            parts.append(f" {ln}| {a.content}  // [MODIFIED] 原: {old}")

    return "\n".join(parts)


def format_plain_file(content: str) -> str:
    """格式化普通文件（不带标注，仅行号）。"""
    lines = content.split("\n")
    num_width = max(len(str(len(lines))), 3)
    parts = []
    for i, line in enumerate(lines, start=1):
        ln = str(i).rjust(num_width)
        parts.append(f" {ln}| {line}")
    return "\n".join(parts)
