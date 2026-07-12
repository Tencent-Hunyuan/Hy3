from __future__ import annotations

import pytest

from apps.incident_agent.demos import DEMOS, get_demo
from apps.incident_agent.workspace import (
    WorkspaceError,
    incident_workspace,
    validate_files,
)


def test_two_demos_cover_retry_and_worker_incidents():
    assert [demo.id for demo in DEMOS] == ["retry-regression", "worker-startup"]
    assert "test_client.py" in get_demo("retry-regression").files
    assert "startup.log" in get_demo("worker-startup").files


def test_unknown_demo_is_rejected():
    with pytest.raises(KeyError, match="Unknown demo: missing"):
        get_demo("missing")


def test_workspace_writes_utf8_files_and_cleans_up():
    with incident_workspace([("service.py", b"value = 1\n")]) as root:
        saved_root = root
        assert (root / "service.py").read_text(encoding="utf-8") == "value = 1\n"

    assert not saved_root.exists()


@pytest.mark.parametrize("name", ["../secret.py", "nested/file.py", "binary.exe"])
def test_invalid_names_are_rejected(name):
    with pytest.raises(WorkspaceError):
        validate_files([(name, b"text")])


def test_binary_encoding_and_limits_are_rejected():
    invalid_cases = [
        [("bad.txt", b"\x00binary")],
        [("bad.txt", b"\xff")],
        [(f"{index}.txt", b"x") for index in range(9)],
        [("large.txt", b"x" * (512 * 1024 + 1))],
        [("same.txt", b"one"), ("same.txt", b"two")],
        [(f"{index}.txt", b"x" * (512 * 1024)) for index in range(5)],
    ]

    for files in invalid_cases:
        with pytest.raises(WorkspaceError):
            validate_files(files)
