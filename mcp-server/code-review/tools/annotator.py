"""
行标注引擎 — 从 diff hunk 解析变更行，给文件内容逐行标注 [ADDED]/[MODIFIED]/[UNCHANGED]。

输入: 文件完整内容 + 该文件的 git diff
输出: 每行带上标注的 AnnotatedLine 列表

核心算法:
  遍历 diff 的 hunk body:
    空格开头 → 上下文，两个行号都+1，清空配对队列
    + 开头   → 新增行
               配对队列非空 → pop 配对 → [MODIFIED] + 旧内容
               配对队列为空 → [ADDED]
    - 开头   → 删除行 → 进入配对队列，等待下一个 + 来配对
"""

import re
from tools.types import HunkInfo, AnnotatedLine

# 匹配 hunk header: @@ -old_start,old_count +new_start,new_count @@ context
HUNK_HEADER_RE = re.compile(
    r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@\s*(.*)$"
)


def parse_hunks(diff_text: str) -> list[HunkInfo]:
    """从 diff 文本中解析所有 hunk header。

    只提取位置信息，不处理 hunk body（body 由 annotate_lines 处理）。
    """
    hunks = []
    for line in diff_text.split("\n"):
        m = HUNK_HEADER_RE.match(line)
        if m:
            hunks.append(HunkInfo(
                old_start=int(m.group(1)),
                old_count=int(m.group(2) or 1),
                new_start=int(m.group(3)),
                new_count=int(m.group(4) or 1),
                context=m.group(5).strip(),
            ))
    return hunks


def annotate_lines(file_content: str, diff_text: str) -> list[AnnotatedLine]:
    """对文件完整内容进行逐行标注。

    Args:
        file_content: 文件完整文本（工作区当前版本）
        diff_text: 该文件的 git diff 输出

    Returns:
        AnnotatedLine 列表，与 file_content 的行一一对应
    """
    # Step 1: 从 diff 构建 行号→标注 的映射
    annotation_map = _build_annotation_map(diff_text)

    # Step 2: 逐行应用标注
    result = []
    for i, content in enumerate(file_content.split("\n"), start=1):
        entry = annotation_map.get(i, "UNCHANGED")
        if isinstance(entry, tuple):
            ann, old = entry
        else:
            ann, old = entry, None

        result.append(AnnotatedLine(
            line_number=i,
            content=content,
            annotation=ann,
            old_content=old,
        ))

    return result


def _build_annotation_map(diff_text: str) -> dict[int, str | tuple]:
    """从 diff 的 hunk body 构建 {新文件行号: 标注} 的映射。

    状态机遍历每个 hunk:
       状态变量:
         new_line       — 新文件的当前行号
         removed_queue  — 待配对的删除行队列

       每行处理:
         '@@'  → 进入 hunk，重置状态
         ' '   → 上下文行，清空队列
         '-'   → 删除行，入队
         '+'   → 队列非空 → MODIFIED，否则 ADDED
    """
    annotations: dict = {}

    in_hunk = False
    new_line = 0
    removed_queue: list[str] = []

    for line in diff_text.split("\n"):
        # ── hunk header ──
        m = HUNK_HEADER_RE.match(line)
        if m:
            in_hunk = True
            new_line = int(m.group(3))
            removed_queue.clear()
            continue

        if not in_hunk:
            continue

        # ── 跳过元数据行 ──
        if (line.startswith("diff ") or line.startswith("index ") or
                line.startswith("---") or line.startswith("+++") or
                line.startswith("@@") or line.startswith("\\")):
            continue

        # ── 空行视为上下文 ──
        if not line:
            new_line += 1
            continue

        prefix = line[0]
        content = line[1:]

        if prefix == " ":
            # 上下文 — 打断配对
            removed_queue.clear()
            new_line += 1

        elif prefix == "-":
            # 删除 — 等待配对
            removed_queue.append(content)

        elif prefix == "+":
            # 新增
            if removed_queue:
                old_text = removed_queue.pop(0)
                annotations[new_line] = ("MODIFIED", old_text)
            else:
                annotations[new_line] = "ADDED"
            new_line += 1

    return annotations
