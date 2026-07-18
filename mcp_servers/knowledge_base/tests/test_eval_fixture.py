from __future__ import annotations

import os
import shutil
from datetime import timedelta
from pathlib import Path
from xml.etree import ElementTree

import anyio
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from scripts.run_eval import build_child_environment, parse_evaluation

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def test_evaluation_has_ten_unique_read_only_questions() -> None:
    root = ElementTree.parse(PACKAGE_ROOT / "eval" / "evaluation.xml").getroot()
    pairs = root.findall("qa_pair")
    questions = [pair.findtext("question", "").strip() for pair in pairs]
    answers = [pair.findtext("answer", "").strip() for pair in pairs]
    sources = [
        [item.text.strip() for item in pair.findall("source") if item.text] for pair in pairs
    ]

    assert len(pairs) == 10
    assert len(set(questions)) == 10
    assert all(questions)
    assert all(answers)
    assert all(sources)
    assert any(any("\u4e00" <= char <= "\u9fff" for char in question) for question in questions)
    assert any(len(items) > 1 for items in sources)


def test_fixture_contains_no_secret_or_dynamic_answer() -> None:
    corpus = PACKAGE_ROOT / "examples" / "knowledge_base"
    text = "\n".join(path.read_text(encoding="utf-8") for path in sorted(corpus.iterdir()))

    assert "sk-or-" not in text
    assert "current date" not in text.lower()
    assert "today" not in text.lower()


def test_fixture_declares_canonical_exact_answers_for_strict_cases() -> None:
    corpus = PACKAGE_ROOT / "examples" / "knowledge_base"

    incident = (corpus / "incident-review.md").read_text(encoding="utf-8")
    architecture = (corpus / "architecture.md").read_text(encoding="utf-8")
    runbook = (corpus / "runbook.txt").read_text(encoding="utf-8")

    assert "Exact answer token: 27." in incident
    assert "Exact two-word mechanism: LIKE fallback." in architecture
    assert "Exact two-word action: Stop indexing." in runbook


@pytest.mark.anyio
async def test_offline_stdio_retrieval_preflight_covers_every_declared_source(
    tmp_path: Path,
) -> None:
    corpus = PACKAGE_ROOT / "examples" / "knowledge_base"
    report_path = PACKAGE_ROOT / "eval" / "report.md"
    report_before = report_path.read_bytes()
    storage = tmp_path / "isolated-storage"
    stale_storage = tmp_path / "stale-global-storage"
    stale_corpus = tmp_path / "stale-corpus"
    stale_corpus.mkdir()
    (stale_corpus / "stale.md").write_text("stale evaluation collection", encoding="utf-8")
    parent = {
        key: value
        for key, value in os.environ.items()
        if key.upper()
        in {
            "COMSPEC",
            "HOME",
            "LANG",
            "LC_ALL",
            "LOCALAPPDATA",
            "PATH",
            "PATHEXT",
            "SYSTEMROOT",
            "TEMP",
            "TMP",
            "TMPDIR",
            "USERPROFILE",
            "WINDIR",
        }
    }
    parent.update(
        {
            "HY3_API_KEY": "must-not-reach-offline-server",
            "HY3_KB_STORAGE_DIR": os.fspath(stale_storage),
            "PYTHON_DOTENV_DISABLED": "0",
        }
    )
    child = build_child_environment(parent, corpus, storage)
    child.pop("HY3_API_KEY")
    assert "HY3_API_KEY" not in child
    assert child["PYTHON_DOTENV_DISABLED"] == "1"
    command = shutil.which("hy3-knowledge-mcp")
    assert command is not None
    stale_child = build_child_environment(parent, stale_corpus, stale_storage)
    stale_child.pop("HY3_API_KEY")
    assert "HY3_API_KEY" not in stale_child
    stale_server = StdioServerParameters(
        command=command,
        args=[],
        cwd=PACKAGE_ROOT,
        env=stale_child,
        encoding="utf-8",
        encoding_error_handler="strict",
    )
    with anyio.fail_after(20):
        async with stdio_client(stale_server) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                stale_indexed = await session.call_tool(
                    "hy3_kb_index_documents",
                    arguments={
                        "collection": "evaluation",
                        "path": os.fspath(stale_corpus),
                        "replace": True,
                    },
                )
                assert stale_indexed.isError is False

    server = StdioServerParameters(
        command=command,
        args=[],
        cwd=PACKAGE_ROOT,
        env=child,
        encoding="utf-8",
        encoding_error_handler="strict",
    )

    with anyio.fail_after(30):
        async with stdio_client(server) as (read, write):
            async with ClientSession(
                read,
                write,
                read_timeout_seconds=timedelta(seconds=15),
            ) as session:
                await session.initialize()
                indexed = await session.call_tool(
                    "hy3_kb_index_documents",
                    arguments={
                        "collection": "evaluation",
                        "path": os.fspath(corpus),
                        "replace": True,
                    },
                )
                assert indexed.isError is False
                listed = await session.call_tool(
                    "hy3_kb_list_sources",
                    arguments={"collection": "evaluation", "limit": 20},
                )
                assert listed.isError is False
                listed_sources = listed.structuredContent["sources"]
                assert len(listed_sources) == 6

                for case in parse_evaluation(PACKAGE_ROOT / "eval" / "evaluation.xml"):
                    searched = await session.call_tool(
                        "hy3_kb_search",
                        arguments={
                            "collection": "evaluation",
                            "query": case.question,
                            "limit": 12,
                        },
                    )
                    assert searched.isError is False
                    hit_sources = tuple(
                        item["source_path"] for item in searched.structuredContent["results"]
                    )
                    for source in case.sources:
                        assert any(item.endswith(source) for item in hit_sources), (
                            case.question,
                            source,
                            hit_sources,
                        )

    assert report_path.read_bytes() == report_before
    assert (stale_storage / "index.sqlite3").is_file()
    assert (storage / "index.sqlite3").is_file()
