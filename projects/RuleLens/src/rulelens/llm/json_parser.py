"""模型返回文本 -> JSON 的健壮解析。

依次尝试：
1. 直接 ``json.loads``；
2. 去除 Markdown 代码围栏（```json ... ```）；
3. 截取最外层 JSON 对象（处理前后说明文字）。

明确禁止 ``eval``，解析失败给出明确错误信息，不静默丢弃必填字段。
"""

from __future__ import annotations

import json


class JsonParseError(Exception):
    """模型返回内容无法解析为 JSON 对象。"""


def _strip_code_fences(text: str) -> str:
    s = text.strip()
    if s.startswith("```"):
        nl = s.find("\n")
        if nl != -1:
            s = s[nl + 1 :]
        if s.rstrip().endswith("```"):
            s = s.rstrip()[:-3]
        s = s.strip()
    return s


def _extract_outermost_object(text: str) -> str | None:
    """在文本中找到第一个完整的最外层 { ... }。"""
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def extract_json_object(text: str) -> dict:
    """从模型返回文本中提取并解析为 dict。

    :raises JsonParseError: 任何阶段都无法得到合法 JSON 对象。
    """
    if not text or not text.strip():
        raise JsonParseError("模型返回内容为空，无法解析 JSON。")

    candidate = text.strip()

    # 1. 直接解析
    try:
        obj = json.loads(candidate)
        if isinstance(obj, dict):
            return obj
    except (json.JSONDecodeError, ValueError):
        pass

    # 2. 去除代码围栏
    fenced = _strip_code_fences(candidate)
    if fenced != candidate:
        try:
            obj = json.loads(fenced)
            if isinstance(obj, dict):
                return obj
        except (json.JSONDecodeError, ValueError):
            pass

    # 3. 截取最外层对象
    outer = _extract_outermost_object(candidate)
    if outer is not None:
        try:
            obj = json.loads(outer)
            if isinstance(obj, dict):
                return obj
        except (json.JSONDecodeError, ValueError) as exc:
            raise JsonParseError(f"提取到 JSON 片段但解析失败：{exc}") from exc

    raise JsonParseError("未找到可解析的 JSON 对象，请检查模型输出。")
