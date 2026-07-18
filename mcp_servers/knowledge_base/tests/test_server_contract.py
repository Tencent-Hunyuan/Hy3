import json
from pathlib import Path

import anyio
import pytest
from mcp.shared.memory import create_connected_server_and_client_session
from mcp.types import TextContent

import hy3_knowledge_mcp.server as server_module
import hy3_knowledge_mcp.services as services_module
from hy3_knowledge_mcp.models import (
    AskResult,
    Hy3AnswerPayload,
    Hy3SummaryPayload,
    IndexDocumentsResult,
    ListSourcesResult,
    SearchResult,
    SummaryResult,
)
from hy3_knowledge_mcp.server import mcp
from hy3_knowledge_mcp.services import KnowledgeBaseService


@pytest.mark.anyio
async def test_server_exposes_exactly_five_tools(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    monkeypatch.setenv("HY3_KB_ROOTS", str(root))
    monkeypatch.setenv("HY3_KB_STORAGE_DIR", str(tmp_path / "storage"))

    async with create_connected_server_and_client_session(
        mcp,
        raise_exceptions=True,
    ) as session:
        tools = {tool.name for tool in (await session.list_tools()).tools}

    assert tools == {
        "hy3_kb_index_documents",
        "hy3_kb_search",
        "hy3_kb_ask",
        "hy3_kb_summarize_source",
        "hy3_kb_list_sources",
    }


@pytest.mark.anyio
async def test_tools_publish_flat_business_schemas_and_annotations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    monkeypatch.setenv("HY3_KB_ROOTS", str(root))
    monkeypatch.setenv("HY3_KB_STORAGE_DIR", str(tmp_path / "storage"))

    async with create_connected_server_and_client_session(mcp) as session:
        tools = {tool.name: tool for tool in (await session.list_tools()).tools}

    expected_outputs = {
        "hy3_kb_index_documents": "indexed_sources",
        "hy3_kb_search": "results",
        "hy3_kb_ask": "answer",
        "hy3_kb_summarize_source": "used_evidence_ids",
        "hy3_kb_list_sources": "sources",
    }
    for name, output_property in expected_outputs.items():
        tool = tools[name]
        assert "ctx" not in tool.inputSchema["properties"]
        assert "params" not in tool.inputSchema["properties"]
        assert tool.outputSchema is not None
        assert output_property in tool.outputSchema["properties"]
        assert "content" not in tool.outputSchema["properties"]
        assert tool.annotations is not None
        assert tool.annotations.destructiveHint is False

    search = tools["hy3_kb_search"]
    search_properties = search.inputSchema["properties"]
    assert search_properties["limit"] == {
        "default": 8,
        "maximum": 20,
        "minimum": 1,
        "title": "Limit",
        "type": "integer",
    }
    assert search_properties["offset"]["default"] == 0
    assert search_properties["offset"]["minimum"] == 0
    assert search.inputSchema["$defs"]["ResponseFormat"]["enum"] == ["markdown", "json"]
    assert search.annotations.readOnlyHint is True
    assert search.annotations.idempotentHint is True
    assert search.annotations.openWorldHint is False

    ask = tools["hy3_kb_ask"]
    assert ask.inputSchema["properties"]["top_k"]["maximum"] == 12
    assert ask.inputSchema["$defs"]["ReasoningEffort"]["enum"] == ["none", "low", "high"]
    assert ask.annotations.readOnlyHint is True
    assert ask.annotations.idempotentHint is False
    assert ask.annotations.openWorldHint is True

    summary_source = tools["hy3_kb_summarize_source"].inputSchema["properties"]["source_path"]
    assert summary_source["minLength"] == 1
    assert summary_source["maxLength"] == 4096

    index = tools["hy3_kb_index_documents"]
    assert index.annotations.readOnlyHint is False
    assert index.annotations.idempotentHint is True
    assert index.annotations.openWorldHint is False

    listed = tools["hy3_kb_list_sources"]
    assert listed.inputSchema["properties"]["limit"]["maximum"] == 100
    assert listed.annotations.readOnlyHint is True
    assert listed.annotations.idempotentHint is True
    assert listed.annotations.openWorldHint is False


@pytest.mark.anyio
async def test_offline_tools_return_exact_structured_models_and_json_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "guide.md").write_text(
        "# Hy3\n\nHy3 supports deliberate reasoning.",
        encoding="utf-8",
    )
    monkeypatch.setenv("HY3_KB_ROOTS", str(root))
    monkeypatch.setenv("HY3_KB_STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.delenv("HY3_API_KEY", raising=False)

    async with create_connected_server_and_client_session(mcp) as session:
        indexed = await session.call_tool(
            "hy3_kb_index_documents",
            arguments={"collection": "docs", "path": str(root)},
        )
        searched = await session.call_tool(
            "hy3_kb_search",
            arguments={
                "collection": "docs",
                "query": "deliberate reasoning",
                "response_format": "json",
            },
        )
        listed = await session.call_tool(
            "hy3_kb_list_sources",
            arguments={"collection": "docs", "response_format": "json"},
        )

    assert indexed.isError is False
    assert searched.isError is False
    assert listed.isError is False
    assert indexed.structuredContent == IndexDocumentsResult.model_validate(
        indexed.structuredContent
    ).model_dump(mode="json")
    assert searched.structuredContent == SearchResult.model_validate(
        searched.structuredContent
    ).model_dump(mode="json")
    assert listed.structuredContent == ListSourcesResult.model_validate(
        listed.structuredContent
    ).model_dump(mode="json")
    assert isinstance(searched.content[0], TextContent)
    assert isinstance(listed.content[0], TextContent)
    assert json.loads(searched.content[0].text) == searched.structuredContent
    assert json.loads(listed.content[0].text) == listed.structuredContent


@pytest.mark.anyio
async def test_validation_and_domain_errors_are_safe_tool_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "sensitive-root"
    root.mkdir()
    secret = "do-not-leak-this-api-key"
    monkeypatch.setenv("HY3_KB_ROOTS", str(root))
    monkeypatch.setenv("HY3_KB_STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setenv("HY3_API_KEY", secret)

    search_called = False
    original_search = KnowledgeBaseService.search

    async def observe_search(self: KnowledgeBaseService, request: object) -> SearchResult:
        nonlocal search_called
        search_called = True
        return await original_search(self, request)  # type: ignore[arg-type]

    monkeypatch.setattr(KnowledgeBaseService, "search", observe_search)

    async with create_connected_server_and_client_session(mcp) as session:
        invalid = await session.call_tool(
            "hy3_kb_search",
            arguments={
                "collection": "docs",
                "query": "Hy3",
                "source_paths": ["root/file.md\u0000hidden"],
            },
        )
        assert search_called is False
        missing = await session.call_tool(
            "hy3_kb_list_sources",
            arguments={"collection": "missing"},
        )

    assert invalid.isError is True
    assert missing.isError is True
    error_text = "\n".join(
        item.text
        for result in (invalid, missing)
        for item in result.content
        if isinstance(item, TextContent)
    )
    assert "Traceback" not in error_text
    assert str(root) not in error_text
    assert secret not in error_text
    assert "index" in error_text.lower() or "知识库" in error_text


@pytest.mark.anyio
async def test_ask_is_lazy_offline_for_zero_hits_and_maps_missing_remote_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "guide.md").write_text("Hy3 supports reasoning.", encoding="utf-8")
    monkeypatch.setenv("HY3_KB_ROOTS", str(root))
    monkeypatch.setenv("HY3_KB_STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setenv("HY3_ENDPOINT_PROFILE", "generic")
    monkeypatch.setenv("HY3_BASE_URL", "https://example.invalid/v1")
    monkeypatch.delenv("HY3_API_KEY", raising=False)

    async with create_connected_server_and_client_session(mcp) as session:
        await session.call_tool(
            "hy3_kb_index_documents",
            arguments={"collection": "docs", "path": str(root)},
        )
        zero_hit = await session.call_tool(
            "hy3_kb_ask",
            arguments={"collection": "docs", "question": "unfindable-zebra-token"},
        )
        remote = await session.call_tool(
            "hy3_kb_ask",
            arguments={"collection": "docs", "question": "reasoning"},
        )
        listed_after_error = await session.call_tool(
            "hy3_kb_list_sources",
            arguments={"collection": "docs"},
        )

    assert zero_hit.isError is False
    zero_payload = AskResult.model_validate(zero_hit.structuredContent)
    assert zero_payload.insufficient_evidence is True
    assert zero_payload.citations == ()
    assert remote.isError is True
    assert isinstance(remote.content[0], TextContent)
    assert "HY3_API_KEY" in remote.content[0].text
    assert "Traceback" not in remote.content[0].text
    assert listed_after_error.isError is False


@pytest.mark.anyio
async def test_in_memory_sessions_capture_independent_environment_and_storage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_root = tmp_path / "first-root"
    second_root = tmp_path / "second-root"
    first_root.mkdir()
    second_root.mkdir()
    (first_root / "first.md").write_text("first session evidence", encoding="utf-8")
    (second_root / "second.md").write_text("second session evidence", encoding="utf-8")

    monkeypatch.setenv("HY3_KB_ROOTS", str(first_root))
    monkeypatch.setenv("HY3_KB_STORAGE_DIR", str(tmp_path / "first-storage"))
    async with create_connected_server_and_client_session(mcp) as first_session:
        first_index = await first_session.call_tool(
            "hy3_kb_index_documents",
            arguments={"collection": "docs", "path": str(first_root)},
        )
        assert first_index.isError is False

        monkeypatch.setenv("HY3_KB_ROOTS", str(second_root))
        monkeypatch.setenv("HY3_KB_STORAGE_DIR", str(tmp_path / "second-storage"))
        async with create_connected_server_and_client_session(mcp) as second_session:
            second_index = await second_session.call_tool(
                "hy3_kb_index_documents",
                arguments={"collection": "docs", "path": str(second_root)},
            )
            first_search = await first_session.call_tool(
                "hy3_kb_search",
                arguments={"collection": "docs", "query": "first"},
            )
            second_search = await second_session.call_tool(
                "hy3_kb_search",
                arguments={"collection": "docs", "query": "second"},
            )
            crossed_search = await second_session.call_tool(
                "hy3_kb_search",
                arguments={"collection": "docs", "query": "first"},
            )

    assert second_index.isError is False
    assert SearchResult.model_validate(first_search.structuredContent).count == 1
    assert SearchResult.model_validate(second_search.structuredContent).count == 1
    assert SearchResult.model_validate(crossed_search.structuredContent).count == 0


@pytest.mark.anyio
async def test_session_teardown_closes_service_despite_server_cancellation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    monkeypatch.setenv("HY3_KB_ROOTS", str(root))
    monkeypatch.setenv("HY3_KB_STORAGE_DIR", str(tmp_path / "storage"))
    close_events: list[str] = []

    class ClosingService:
        def __init__(self, **_kwargs: object) -> None:
            pass

        async def close(self) -> None:
            close_events.append("started")
            await anyio.sleep(0)
            close_events.append("finished")

    monkeypatch.setattr(server_module, "KnowledgeBaseService", ClosingService)

    async with create_connected_server_and_client_session(mcp) as session:
        assert len((await session.list_tools()).tools) == 5

    assert close_events == ["started", "finished"]


@pytest.mark.anyio
async def test_remote_tools_render_markdown_and_exact_json_without_network(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "guide.md").write_text("Hy3 supports deliberate reasoning.", encoding="utf-8")
    monkeypatch.setenv("HY3_KB_ROOTS", str(root))
    monkeypatch.setenv("HY3_KB_STORAGE_DIR", str(tmp_path / "storage"))

    class FakeHy3Client:
        def __init__(self, _settings: object) -> None:
            pass

        async def answer(self, _messages: object, **_kwargs: object) -> Hy3AnswerPayload:
            return Hy3AnswerPayload(
                answer="Hy3 supports deliberate reasoning.",
                used_evidence_ids=("S1",),
                insufficient_evidence=False,
            )

        async def summarize(self, _messages: object, **_kwargs: object) -> Hy3SummaryPayload:
            return Hy3SummaryPayload(
                summary="A concise Hy3 reasoning guide.",
                used_evidence_ids=("S1",),
            )

        async def close(self) -> None:
            pass

    monkeypatch.setattr(services_module, "Hy3Client", FakeHy3Client)

    async with create_connected_server_and_client_session(mcp) as session:
        await session.call_tool(
            "hy3_kb_index_documents",
            arguments={"collection": "docs", "path": str(root)},
        )
        listed = await session.call_tool(
            "hy3_kb_list_sources",
            arguments={"collection": "docs"},
        )
        source_path = listed.structuredContent["sources"][0]["source_path"]  # type: ignore[index]
        asked = await session.call_tool(
            "hy3_kb_ask",
            arguments={
                "collection": "docs",
                "question": "What does Hy3 support?",
                "response_format": "json",
            },
        )
        summary_json = await session.call_tool(
            "hy3_kb_summarize_source",
            arguments={
                "collection": "docs",
                "source_path": source_path,
                "response_format": "json",
            },
        )
        summary_markdown = await session.call_tool(
            "hy3_kb_summarize_source",
            arguments={"collection": "docs", "source_path": source_path},
        )

    assert asked.isError is False
    assert summary_json.isError is False
    assert summary_markdown.isError is False
    assert asked.structuredContent == AskResult.model_validate(asked.structuredContent).model_dump(
        mode="json"
    )
    assert summary_json.structuredContent == SummaryResult.model_validate(
        summary_json.structuredContent
    ).model_dump(mode="json")
    assert isinstance(asked.content[0], TextContent)
    assert isinstance(summary_json.content[0], TextContent)
    assert isinstance(summary_markdown.content[0], TextContent)
    assert json.loads(asked.content[0].text) == asked.structuredContent
    assert json.loads(summary_json.content[0].text) == summary_json.structuredContent
    assert "## Citations" in summary_markdown.content[0].text


def test_main_starts_stdio_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    transports: list[str] = []

    def record_run(*, transport: str) -> None:
        transports.append(transport)

    monkeypatch.setattr(mcp, "run", record_run)

    server_module.main()

    assert transports == ["stdio"]


@pytest.mark.anyio
async def test_fastmcp_schema_validation_remains_at_the_public_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    monkeypatch.setenv("HY3_KB_ROOTS", str(root))
    monkeypatch.setenv("HY3_KB_STORAGE_DIR", str(tmp_path / "storage"))

    async with create_connected_server_and_client_session(mcp) as session:
        result = await session.call_tool(
            "hy3_kb_search",
            arguments={"collection": "docs", "query": ""},
        )

    assert result.isError is True
    assert isinstance(result.content[0], TextContent)
    assert "Invalid tool arguments" not in result.content[0].text
    assert "validation error" in result.content[0].text.lower()
