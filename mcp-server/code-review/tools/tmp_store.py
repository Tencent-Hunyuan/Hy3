"""
临时文件存储 — 代码评审过程中暂存 get_file_content 的输出。

每个评审轮次对应一个 tmp 文件，同一轮中多个文件追加写入。
reset_review 时清空所有轮次文件（README.md 除外）。
"""

import os
import uuid

TMP_DIR = os.path.join(os.path.dirname(__file__), "..", "tmp")

_round_number: int = 0
_round_file_path: str | None = None


def init_tmp() -> None:
    """初始化 tmp 目录。"""
    os.makedirs(TMP_DIR, exist_ok=True)
    readme = os.path.join(TMP_DIR, "README.md")
    if not os.path.exists(readme):
        with open(readme, "w", encoding="utf-8") as f:
            f.write(
                "# 临时存储目录\n\n"
                "此目录用于代码评审过程中暂存 `get_file_content` 的输出。\n"
                "每个 `round_N_<uuid>.md` 文件对应一轮评审中混元请求的所有文件。\n"
                "调用 `reset_review` 时自动清空所有轮次文件。\n"
                "本 README.md 不会被删除。\n"
            )


def start_round() -> str:
    """开始新的一轮，创建新的 tmp 文件。返回文件路径。"""
    global _round_number, _round_file_path
    _round_number += 1
    uid = uuid.uuid4().hex[:8]
    _round_file_path = os.path.join(TMP_DIR, f"round_{_round_number}_{uid}.md")
    return _round_file_path


def append_to_round(content: str) -> None:
    """将内容追加写入当前轮的 tmp 文件。如果当前轮不存在则自动创建。"""
    global _round_file_path
    if _round_file_path is None:
        start_round()
    path: str = _round_file_path 
    with open(path, "a", encoding="utf-8") as f:
        f.write(content)
        f.write("\n\n")


def get_round_content() -> str | None:
    """读取当前轮的完整 tmp 文件内容。"""
    if _round_file_path is None or not os.path.isfile(_round_file_path):
        return None
    with open(_round_file_path, "r", encoding="utf-8") as f:
        return f.read()


def get_round_info() -> dict:
    """返回当前轮次信息。"""
    return {
        "round": _round_number,
        "file": os.path.basename(_round_file_path) if _round_file_path else None,
    }


def finish_round() -> None:
    """结束当前轮，为下一轮做准备。"""
    global _round_file_path
    _round_file_path = None


def clear_tmp() -> None:
    """清空所有轮次文件（README.md 除外），重置轮次计数。"""
    global _round_number, _round_file_path
    if not os.path.isdir(TMP_DIR):
        return
    for name in os.listdir(TMP_DIR):
        if name == "README.md":
            continue
        path = os.path.join(TMP_DIR, name)
        try:
            if os.path.isfile(path):
                os.remove(path)
        except OSError:
            pass
    _round_number = 0
    _round_file_path = None
