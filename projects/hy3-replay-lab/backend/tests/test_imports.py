import json
from pathlib import Path

import pytest

from replaylab.imports import ImportRejectedError, parse_imported_task

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def coding_loop_text() -> str:
    return (PROJECT_ROOT / "fixtures" / "coding-loop" / "input.json").read_text(
        encoding="utf-8"
    )


@pytest.mark.parametrize(
    ("filename", "content_type", "content"),
    [
        ("trace.json", "application/json", coding_loop_text()),
        ("trace.txt", "text/plain", coding_loop_text()),
        (
            "trace.md",
            "text/markdown",
            "# Public trace\n\n```replaylab-json\n" + coding_loop_text() + "\n```\n",
        ),
    ],
)
def test_json_markdown_and_text_imports_share_the_strict_task_contract(
    filename: str, content_type: str, content: str
) -> None:
    task = parse_imported_task(
        filename=filename, content_type=content_type, content=content
    )

    assert task.fixture_id == "coding-loop"
    assert task.trace[5].step_id == "step-006-repeat-patch"


@pytest.mark.parametrize(
    ("filename", "content_type"),
    [
        ("../../private.json", "application/json"),
        ("trace.zip", "application/zip"),
        ("trace.json", "text/html"),
        ("CON.json", "application/json"),
    ],
)
def test_malicious_filename_extension_and_mime_are_rejected(
    filename: str, content_type: str
) -> None:
    with pytest.raises(ImportRejectedError):
        parse_imported_task(
            filename=filename,
            content_type=content_type,
            content=coding_loop_text(),
        )


def test_import_byte_budget_and_reference_closure_are_enforced() -> None:
    with pytest.raises(ImportRejectedError, match="文件超过"):
        parse_imported_task(
            filename="large.txt",
            content_type="text/plain",
            content="x" * 128_001,
        )

    payload = json.loads(coding_loop_text())
    payload["trace"][0]["evidence_ids"] = ["unknown-evidence"]
    with pytest.raises(ImportRejectedError, match="任务结构"):
        parse_imported_task(
            filename="invalid.json",
            content_type="application/json",
            content=json.dumps(payload),
        )
