import os

import httpx
import openai
import pytest
from hy3_code_review.server import (
    _extract_content,
    _friendly_error,
    _read_file,
    _run_git_diff,
    _MAX_FILE_BYTES,
    _is_local_host,
)


def test_content_present_returned_verbatim():
    assert _extract_content("real review", None) == "real review"


def test_content_empty_falls_back_to_reasoning_with_annotation():
    out = _extract_content("", "draft thoughts")
    assert "推理过程草稿" in out
    assert "draft thoughts" in out


def test_both_empty_returns_empty_response_notice():
    out = _extract_content("", "")
    assert "空响应" in out


def test_none_inputs_do_not_crash():
    out = _extract_content(None, None)
    assert "空响应" in out


def test_friendly_error_rate_limit():
    req = httpx.Request("POST", "https://x/v1/chat/completions")
    resp = httpx.Response(status_code=429, request=req)
    err = openai.RateLimitError("rate limited", response=resp, body=None)
    out = _friendly_error(err)
    assert "限流" in out


def test_friendly_error_generic_no_traceback():
    out = _friendly_error(ValueError("boom"))
    assert "ValueError" in out
    assert "boom" in out
    assert "Traceback" not in out


def test_read_file_reads_normal_file(tmp_path):
    f = tmp_path / "hello.py"
    f.write_text("print('hi')", encoding="utf-8")
    assert _read_file(str(f)) == "print('hi')"


def test_read_file_rejects_oversized_file(tmp_path):
    f = tmp_path / "big.txt"
    f.write_bytes(b"x" * (_MAX_FILE_BYTES + 1))
    with pytest.raises(ValueError, match="too large"):
        _read_file(str(f))


def test_read_file_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        _read_file(str(tmp_path / "nope.py"))


def test_read_file_sandbox_blocks_outside_path(tmp_path, monkeypatch):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("secret", encoding="utf-8")
    monkeypatch.setenv("HY3_ALLOWED_ROOTS", str(allowed))
    with pytest.raises(PermissionError):
        _read_file(str(outside))


def test_read_file_sandbox_allows_inside_path(tmp_path, monkeypatch):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    inside = allowed / "ok.py"
    inside.write_text("ok", encoding="utf-8")
    monkeypatch.setenv("HY3_ALLOWED_ROOTS", str(allowed))
    assert _read_file(str(inside)) == "ok"


def test_run_git_diff_rejects_flag_injection(tmp_path):
    with pytest.raises(ValueError, match="Invalid base_branch"):
        _run_git_diff(str(tmp_path), "--upload-pack=evil")


def test_run_git_diff_rejects_leading_dash(tmp_path):
    with pytest.raises(ValueError, match="Invalid base_branch"):
        _run_git_diff(str(tmp_path), "-x")


def test_is_local_host_recognizes_local():
    assert _is_local_host("localhost")
    assert _is_local_host("127.0.0.1")
    assert _is_local_host("::1")


def test_is_local_host_rejects_remote():
    assert not _is_local_host("openrouter.ai")
    assert not _is_local_host("10.0.0.5")


def test_is_local_host_true_for_loopback():
    assert _is_local_host("localhost")
    assert _is_local_host("127.0.0.1")
    assert _is_local_host("::1")


def test_is_local_host_false_for_remote():
    assert not _is_local_host("openrouter.ai")
    assert not _is_local_host("10.0.0.5")
