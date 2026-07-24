from pathlib import Path

import pytest

from hy3_evalforge.core.paths import ArtifactStore
from hy3_evalforge.errors import ErrorCode, EvalForgeError


def test_rejects_directory_traversal(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)

    with pytest.raises(EvalForgeError) as raised:
        store.resolve("../outside.txt")

    assert raised.value.code == ErrorCode.PATH_DENIED


def test_rejects_symlink_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    link = tmp_path / "escaped.txt"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symbolic links are unavailable in this environment")

    store = ArtifactStore(tmp_path)
    with pytest.raises(EvalForgeError) as raised:
        store.read_text("escaped.txt")

    assert raised.value.code == ErrorCode.PATH_DENIED


def test_atomic_write_does_not_overwrite_by_default(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    assert store.write_json("artifact.json", {"b": 1, "a": 2}).read_text(encoding="utf-8") == (
        '{\n  "a": 2,\n  "b": 1\n}\n'
    )

    with pytest.raises(EvalForgeError) as raised:
        store.write_text("artifact.json", "replacement")

    assert raised.value.code == ErrorCode.ARTIFACT_CONFLICT


def test_rejects_oversized_input(tmp_path: Path) -> None:
    path = tmp_path / "large.txt"
    path.write_text("12345", encoding="utf-8")

    with pytest.raises(EvalForgeError) as raised:
        ArtifactStore(tmp_path, max_file_bytes=4).read_text(path)

    assert raised.value.code == ErrorCode.INPUT_ERROR
