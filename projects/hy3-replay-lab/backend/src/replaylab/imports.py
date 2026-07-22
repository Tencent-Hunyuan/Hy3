from __future__ import annotations

import json
import re
from pathlib import PurePath
from typing import Any

from pydantic import ValidationError

from replaylab.schemas import TaskSpec

MAX_IMPORT_FILE_BYTES = 128_000
_SAFE_FILENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$")
_RESERVED_WINDOWS_NAMES = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{index}" for index in range(1, 10)),
    *(f"lpt{index}" for index in range(1, 10)),
}
_MIME_BY_SUFFIX = {
    ".json": frozenset({"application/json", "text/json"}),
    ".md": frozenset({"text/markdown"}),
    ".txt": frozenset({"text/plain"}),
}
_MARKDOWN_BLOCK = re.compile(
    r"```(?:replaylab-json|json)\s*\n(?P<payload>\{.*\})\s*\n```",
    flags=re.DOTALL | re.IGNORECASE,
)


class ImportRejectedError(ValueError):
    """Raised with a bounded message when an imported file is unsafe or invalid."""


def parse_imported_task(*, filename: str, content_type: str, content: str) -> TaskSpec:
    suffix = _validate_file_metadata(filename, content_type)
    if "\x00" in content:
        raise ImportRejectedError("文件包含不支持的二进制数据")
    if len(content.encode("utf-8")) > MAX_IMPORT_FILE_BYTES:
        raise ImportRejectedError("文件超过 128000 字节上限")

    candidate = content
    if suffix == ".md":
        matches = list(_MARKDOWN_BLOCK.finditer(content))
        if len(matches) != 1:
            raise ImportRejectedError(
                "Markdown 必须且只能包含一个 replaylab-json 代码块"
            )
        candidate = matches[0].group("payload")
    try:
        payload: Any = json.loads(candidate)
    except json.JSONDecodeError as error:
        raise ImportRejectedError("文件不包含有效的任务 JSON") from error
    if not isinstance(payload, dict):
        raise ImportRejectedError("文件不包含任务对象")
    try:
        return TaskSpec.model_validate(payload)
    except (ValidationError, ValueError) as error:
        raise ImportRejectedError("文件不符合轨迹复盘任务结构") from error


def _validate_file_metadata(filename: str, content_type: str) -> str:
    if (
        not _SAFE_FILENAME.fullmatch(filename)
        or "/" in filename
        or "\\" in filename
        or ".." in filename
    ):
        raise ImportRejectedError("不允许使用该文件名")
    path = PurePath(filename)
    suffix = path.suffix.lower()
    if suffix not in _MIME_BY_SUFFIX:
        raise ImportRejectedError("不支持该文件扩展名")
    if path.stem.casefold() in _RESERVED_WINDOWS_NAMES:
        raise ImportRejectedError("该文件名为系统保留名称")
    normalized_mime = content_type.partition(";")[0].strip().lower()
    if normalized_mime not in _MIME_BY_SUFFIX[suffix]:
        raise ImportRejectedError("内容类型与文件扩展名不匹配")
    return suffix
