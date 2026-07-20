"""共享数据类型。"""

from dataclasses import dataclass


@dataclass
class HunkInfo:
    """diff 中的一个 hunk 块。"""
    old_start: int        # 旧文件起始行号
    old_count: int        # 旧文件行数
    new_start: int        # 新文件起始行号
    new_count: int        # 新文件行数
    context: str = ""     # hunk header 末尾的函数/类名


@dataclass
class AnnotatedLine:
    """一行带标注的代码。"""
    line_number: int           # 行号 (1-based)
    content: str               # 当前行内容
    annotation: str            # 'ADDED' | 'MODIFIED' | 'UNCHANGED'
    old_content: str | None = None  # MODIFIED 时的旧内容
