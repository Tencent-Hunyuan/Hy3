"""JSON 解析单元测试。"""

from __future__ import annotations

import pytest
from pydantic import BaseModel, Field

from rulelens.llm.json_parser import JsonParseError, extract_json_object


class _M(BaseModel):
    a: int
    b: str = Field(min_length=1)


def test_pure_json():
    obj = extract_json_object('{"a": 1, "b": "x"}')
    assert obj == {"a": 1, "b": "x"}


def test_fenced_json():
    text = '好的，结果如下：\n```json\n{"a": 2, "b": "y"}\n```\n以上。'
    obj = extract_json_object(text)
    assert obj["a"] == 2


def test_surrounding_text():
    text = '请参考下面内容：{"a": 3, "b": "z"} 这是补充说明。'
    obj = extract_json_object(text)
    assert obj["a"] == 3


def test_truncated_json_fails():
    with pytest.raises(JsonParseError):
        extract_json_object('{"a": 1, "b": "x"')


def test_invalid_field_fails_pydantic():
    from pydantic import ValidationError

    from rulelens.llm.json_parser import JsonParseError as _JPE  # noqa: F401

    obj = extract_json_object('{"a": "not_int", "b": "ok"}')
    # 解析成功但字段类型不符，Pydantic 会失败
    try:
        _M.model_validate(obj)
    except ValidationError:
        pass
    else:  # pragma: no cover
        raise AssertionError("应当触发 Pydantic 校验失败")


def test_no_code_execution():
    # 含 Python 表达的字符串不应被当作代码执行
    with pytest.raises(JsonParseError):
        extract_json_object("__import__('os').system('echo hacked')")


def test_empty_content_fails():
    with pytest.raises(JsonParseError):
        extract_json_object("   ")
