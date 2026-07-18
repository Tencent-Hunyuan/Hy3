from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from xml.etree import ElementTree

import anyio
import pytest

import scripts.run_eval as run_eval
from scripts.run_eval import (
    EvalFailure,
    EvalMetadata,
    EvalRow,
    _atomic_write_text,
    _evaluate_session,
    build_child_environment,
    corpus_sha256,
    evaluate_row,
    main,
    parse_evaluation,
    render_report,
    safe_endpoint_host,
)

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def _write_evaluation(
    path: Path,
    *,
    defect: str | None = None,
) -> Path:
    root = ElementTree.Element("wrong-root" if defect == "root" else "evaluation")
    count = 9 if defect == "count" else 10
    for index in range(count):
        pair = ElementTree.SubElement(root, "qa_pair")
        question = f"Question {index}"
        answer = f"Answer {index}"
        sources = ["roadmap.md"]
        if index == 0:
            if defect == "blank-question":
                question = "   "
            elif defect == "blank-answer":
                answer = "   "
            elif defect == "no-source":
                sources = []
            elif defect == "blank-source":
                sources = ["   "]
            elif defect == "duplicate-source":
                sources = ["roadmap.md", "roadmap.md"]
            elif defect == "dot-source":
                sources = ["./roadmap.md"]
            elif defect == "parent-source":
                sources = ["../roadmap.md"]
            elif defect == "absolute-source":
                sources = ["/private/roadmap.md"]
            elif defect == "drive-source":
                sources = ["C:/private/roadmap.md"]
            elif defect == "drive-relative-source":
                sources = ["C:private/roadmap.md"]
            elif defect == "backslash-source":
                sources = ["private\\roadmap.md"]
            elif defect == "control-source":
                sources = ["private/roadmap\x01.md"]
            elif defect == "delete-control-source":
                sources = ["private/roadmap\x7f.md"]
            elif defect == "normalizable-source":
                sources = ["docs//roadmap.md"]
        if index == 1 and defect == "duplicate-question":
            question = "Question 0"
        ElementTree.SubElement(pair, "question").text = question
        ElementTree.SubElement(pair, "answer").text = answer
        for source in sources:
            ElementTree.SubElement(pair, "source").text = source
    ElementTree.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
    return path


def test_parse_evaluation_reads_questions_answers_and_sources() -> None:
    cases = parse_evaluation(PACKAGE_ROOT / "eval" / "evaluation.xml")

    assert len(cases) == 10
    assert cases[0].answer == "2025-11-18"
    assert cases[8].sources == ("charter.md", "roadmap.md")


def test_build_child_environment_overrides_storage_and_disables_dotenv(
    tmp_path: Path,
) -> None:
    parent = {
        "PATH": "runtime-path",
        "SYSTEMROOT": "C:\\Windows",
        "HY3_API_KEY": "live-key-value",
        "HY3_MODEL": "route/model",
        "HY3_KB_STORAGE_DIR": "C:\\stale-global-index",
        "HY3_KB_ROOTS": "C:\\stale-root",
        "PYTHON_DOTENV_DISABLED": "0",
        "UNRELATED_SECRET": "must-not-cross-boundary",
    }
    knowledge_root = tmp_path / "corpus"
    storage_dir = tmp_path / "fresh-storage"

    child = build_child_environment(parent, knowledge_root, storage_dir)

    assert child["HY3_KB_STORAGE_DIR"] == str(storage_dir.resolve())
    assert child["HY3_KB_ROOTS"] == str(knowledge_root.resolve())
    assert child["PYTHON_DOTENV_DISABLED"] == "1"
    assert child["PYTHONUTF8"] == "1"
    assert child["HY3_API_KEY"] == "live-key-value"
    assert child["HY3_MODEL"] == "route/model"
    assert child["PATH"] == "runtime-path"
    assert child["SYSTEMROOT"] == "C:\\Windows"
    assert "UNRELATED_SECRET" not in child
    assert "C:\\stale-global-index" not in child.values()


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://openrouter.ai/api/v1?token=secret", "openrouter.ai"),
        ("http://127.0.0.1:8000/v1", "127.0.0.1:8000"),
        ("https://[::1]:9443/v1", "[::1]:9443"),
        ("https://user:secret@example.com/v1", "unavailable"),
        ("not-a-url", "unavailable"),
    ],
)
def test_safe_endpoint_host_never_returns_credentials_or_path(url: str, expected: str) -> None:
    assert safe_endpoint_host(url) == expected


def test_corpus_digest_is_independent_of_absolute_root(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    for root in (first, second):
        root.mkdir()
        (root / "a.md").write_bytes(b"alpha")
        (root / "b.txt").write_bytes(b"beta")

    assert corpus_sha256(first) == corpus_sha256(second)


def test_evaluate_row_requires_exact_answer_and_all_source_suffixes() -> None:
    row = evaluate_row(
        number=1,
        question="Question",
        expected_answer="Mei Lin",
        declared_sources=("charter.md", "roadmap.md"),
        search_sources=("root-1/charter.md", "root-1/roadmap.md"),
        actual_answer="  MEI LIN  ",
        citation_sources=("root-1/roadmap.md", "root-1/charter.md"),
        duration_seconds=1.234,
    )

    assert row.passed is True
    assert row.failure == ""
    assert row.duration_seconds == 1.234


def test_render_report_contains_measured_metadata_without_sensitive_values(
    tmp_path: Path,
) -> None:
    metadata = EvalMetadata(
        model="tencent/hy3:free",
        endpoint_profile="openrouter",
        reasoning_effort="high",
        package_version="0.1.0",
        git_commit="abc1234",
        corpus_sha256="f" * 64,
        endpoint_host="openrouter.ai",
        timestamp_utc=datetime(2026, 7, 11, 1, 2, 3, tzinfo=timezone.utc),
        search_limit=12,
        ask_top_k=12,
    )
    rows = (
        EvalRow(
            number=1,
            question="Question",
            expected_answer="2025-11-18",
            actual_answer="2025-11-18",
            declared_sources=("roadmap.md",),
            search_sources=("root-id/roadmap.md", "root-id/architecture.md"),
            citation_sources=("root-id/roadmap.md",),
            duration_seconds=0.75,
            passed=True,
            failure="",
        ),
    )

    report = render_report(metadata, rows)

    assert "- Questions: 1" in report
    assert "- Score: 1/1 (100.0%)" in report
    assert "- Endpoint host: openrouter.ai" in report
    assert "2026-07-11T01:02:03Z" in report
    assert "roadmap.md" in report
    assert "architecture.md" in report
    assert "| Question |" in report
    assert "| Search hits |" in report
    assert "| Citations |" in report
    assert str(tmp_path.resolve()) not in report
    assert "HY3_API_KEY" not in report
    assert "live-key-value" not in report
    assert "root-id/roadmap.md" not in report


class _FakeSession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, object],
    ) -> SimpleNamespace:
        self.calls.append((name, arguments))
        if name == "hy3_kb_index_documents":
            return SimpleNamespace(isError=False, structuredContent={})
        if name == "hy3_kb_search":
            question = str(arguments["query"])
            source = "root-id/architecture.md" if question == "covered" else "root-id/other.md"
            return SimpleNamespace(
                isError=False,
                structuredContent={"results": [{"source_path": source}]},
            )
        if name == "hy3_kb_ask":
            return SimpleNamespace(
                isError=False,
                structuredContent={
                    "answer": "Answer Engine",
                    "citations": [{"source_path": "root-id/architecture.md"}],
                },
            )
        raise AssertionError(name)


def test_evaluate_session_searches_before_ask_and_skips_failed_preflight(
    tmp_path: Path,
) -> None:
    session = _FakeSession()
    cases = (
        SimpleNamespace(
            question="covered",
            answer="Answer Engine",
            sources=("architecture.md",),
        ),
        SimpleNamespace(
            question="missing",
            answer="Restricted",
            sources=("security-policy.rst",),
        ),
    )

    rows = anyio.run(
        _evaluate_session,
        session,
        cases,
        tmp_path,
        12,
        12,
    )

    assert [name for name, _ in session.calls] == [
        "hy3_kb_index_documents",
        "hy3_kb_search",
        "hy3_kb_ask",
        "hy3_kb_search",
    ]
    assert session.calls[0][1]["replace"] is True
    assert session.calls[0][1]["collection"] == "evaluation"
    assert rows[0].passed is True
    assert rows[1].failure == "retrieval preflight missing: security-policy.rst"
    assert rows[1].actual_answer == "not called"


def test_main_without_api_key_fails_without_creating_report(tmp_path: Path) -> None:
    output = tmp_path / "report.md"
    output.write_text("stale report", encoding="utf-8")

    exit_code = main(
        [
            "--evaluation",
            os.fspath(PACKAGE_ROOT / "eval" / "evaluation.xml"),
            "--knowledge-root",
            os.fspath(PACKAGE_ROOT / "examples" / "knowledge_base"),
            "--output",
            os.fspath(output),
        ],
        environ={"HY3_MODEL": "hy3"},
    )

    assert exit_code == 1
    assert not output.exists()


def test_atomic_write_text_cleans_temp_when_replace_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "report.md"

    def fail_replace(_source: object, _target: object) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr(run_eval.os, "replace", fail_replace)

    with pytest.raises(EvalFailure, match="report write failed"):
        _atomic_write_text(output, "partial report")

    assert not output.exists()
    assert list(tmp_path.glob(".report.md.*.tmp")) == []
