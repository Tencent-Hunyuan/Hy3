import json
from pathlib import Path

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from hy3_taskrelay.server import create_server
from hy3_taskrelay.service import TaskRelayService


class NoCallProvider:
    def __init__(self) -> None:
        self.calls = 0

    async def complete(self, messages: list[dict[str, str]]) -> str:
        self.calls += 1
        raise AssertionError("tools/list must not call Hy3")


class SequenceProvider:
    def __init__(self, responses: list[dict[str, object]]) -> None:
        self._responses = [json.dumps(response) for response in responses]

    async def complete(self, messages: list[dict[str, str]]) -> str:
        return self._responses.pop(0)


@pytest.mark.asyncio
async def test_tools_list_exposes_exactly_three_read_only_taskrelay_tools() -> None:
    server = create_server(TaskRelayService(NoCallProvider()))

    async with create_connected_server_and_client_session(server) as session:
        result = await session.list_tools()

    assert {tool.name for tool in result.tools} == {
        "taskrelay_create_checkpoint",
        "taskrelay_audit_checkpoint",
        "taskrelay_create_resume_brief",
    }
    for tool in result.tools:
        assert tool.annotations is not None
        assert tool.annotations.readOnlyHint is True
        assert tool.annotations.destructiveHint is False
        assert tool.annotations.idempotentHint is True
        assert tool.annotations.openWorldHint is True


@pytest.mark.asyncio
async def test_sdk_client_runs_checkpoint_audit_and_resume_workflow() -> None:
    provider = SequenceProvider(
        [
            {
                "goal": "Finish the interrupted fix.",
                "confirmed_facts": [{"text": "The test fails.", "evidence_ids": ["ev_log"]}],
                "constraints": [],
                "decisions": [],
                "open_questions": [],
                "next_steps": [
                    {
                        "action": "Patch the bug.",
                        "verification": "The test passes.",
                        "evidence_ids": ["ev_log"],
                    }
                ],
            },
            {"overall_status": "clean", "findings": []},
            {
                "concise_context": [
                    {"text": "The failing test is reproduced.", "evidence_ids": ["ev_log"]}
                ],
                "next_steps": [
                    {
                        "priority": 1,
                        "action": "Patch the bug.",
                        "validation": "The test passes.",
                        "evidence_ids": ["ev_log"],
                    }
                ],
                "blockers": [],
                "do_not": [],
            },
        ]
    )
    server = create_server(TaskRelayService(provider))
    evidence = [{"evidence_id": "ev_log", "content": "test failed", "source": "log"}]

    async with create_connected_server_and_client_session(server) as session:
        checkpoint_result = await session.call_tool(
            "taskrelay_create_checkpoint",
            {
                "goal": "Finish the interrupted fix.",
                "session_material": "The test failed before the session ended.",
                "evidence": evidence,
            },
        )
        assert checkpoint_result.isError is False
        assert checkpoint_result.structuredContent is not None
        assert checkpoint_result.content[0].text.startswith("Created checkpoint cp_")
        assert json.loads(checkpoint_result.content[1].text) == checkpoint_result.structuredContent

        audit_result = await session.call_tool(
            "taskrelay_audit_checkpoint",
            {"checkpoint": checkpoint_result.structuredContent},
        )
        assert audit_result.isError is False
        assert audit_result.structuredContent is not None

        resume_result = await session.call_tool(
            "taskrelay_create_resume_brief",
            {
                "checkpoint": checkpoint_result.structuredContent,
                "audit": audit_result.structuredContent,
            },
        )

    assert resume_result.isError is False
    assert resume_result.structuredContent is not None
    assert resume_result.structuredContent["next_steps"][0]["priority"] == 1


@pytest.mark.asyncio
async def test_unknown_tool_is_rejected_by_the_protocol_surface() -> None:
    server = create_server(TaskRelayService(NoCallProvider()))

    async with create_connected_server_and_client_session(server) as session:
        result = await session.call_tool("taskrelay_unknown", {})

    assert result.isError is True
    assert "Unknown tool" in result.content[0].text


@pytest.mark.asyncio
async def test_bad_tool_input_is_rejected_before_hy3_is_called() -> None:
    server = create_server(TaskRelayService(NoCallProvider()))

    async with create_connected_server_and_client_session(server) as session:
        result = await session.call_tool(
            "taskrelay_create_checkpoint",
            {
                "goal": "",
                "session_material": "material",
                "evidence": [{"evidence_id": "ev_log", "content": "failure", "source": "log"}],
            },
        )

    assert result.isError is True
    assert "Invalid taskrelay_create_checkpoint input" in result.content[0].text
    assert "goal" in result.content[0].text


@pytest.mark.asyncio
async def test_missing_key_is_an_actionable_tool_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HY3_API_KEY", raising=False)
    server = create_server()

    async with create_connected_server_and_client_session(server) as session:
        result = await session.call_tool(
            "taskrelay_create_checkpoint",
            {
                "goal": "Continue.",
                "session_material": "material",
                "evidence": [{"evidence_id": "ev_log", "content": "failure", "source": "log"}],
            },
        )

    assert result.isError is True
    assert "HY3_API_KEY" in result.content[0].text


def _artifact(name: str) -> dict[str, object]:
    path = Path(__file__).resolve().parents[1] / "docs" / "client_artifacts" / name
    return json.loads(path.read_text(encoding="utf-8"))


def _error_text(result: object) -> str:
    return " ".join(block.text for block in result.content if hasattr(block, "text"))


@pytest.mark.asyncio
async def test_pre_validation_error_does_not_echo_sensitive_input() -> None:
    marker = "password=PRE_VALIDATION_LEAK_MARKER"
    provider = NoCallProvider()
    server = create_server(TaskRelayService(provider))

    async with create_connected_server_and_client_session(server) as session:
        result = await session.call_tool(
            "taskrelay_create_checkpoint",
            {
                "goal": "Continue.",
                "session_material": "material",
                "evidence": [
                    {
                        "evidence_id": "ev_log",
                        "content": "failure",
                        "source": "x" * 500 + marker,
                    }
                ],
            },
        )

    error_text = _error_text(result)
    assert result.isError is True
    assert provider.calls == 0
    assert marker not in error_text
    assert "input_value" not in error_text
    assert "pydantic.dev" not in error_text
    assert "documented field types and limits" in error_text


@pytest.mark.asyncio
async def test_unknown_field_name_is_not_reflected_in_validation_error() -> None:
    marker = "password=LOCATION_LEAK_MARKER"
    provider = NoCallProvider()
    server = create_server(TaskRelayService(provider))

    async with create_connected_server_and_client_session(server) as session:
        result = await session.call_tool(
            "taskrelay_create_checkpoint",
            {
                "goal": "Continue.",
                "session_material": "material",
                "evidence": [
                    {
                        "evidence_id": "ev_log",
                        "content": "failure",
                        "source": "synthetic log",
                        marker: "value",
                    }
                ],
            },
        )

    error_text = _error_text(result)
    assert result.isError is True
    assert provider.calls == 0
    assert marker not in error_text


@pytest.mark.asyncio
async def test_cross_field_validation_error_does_not_echo_request_material() -> None:
    marker = "CROSS_FIELD_LEAK_MARKER"
    provider = NoCallProvider()
    server = create_server(TaskRelayService(provider))
    evidence = {
        "evidence_id": "ev_duplicate",
        "content": marker,
        "source": "synthetic log",
    }

    async with create_connected_server_and_client_session(server) as session:
        result = await session.call_tool(
            "taskrelay_create_checkpoint",
            {
                "goal": "Continue.",
                "session_material": "material",
                "evidence": [evidence, evidence],
            },
        )

    error_text = _error_text(result)
    assert result.isError is True
    assert provider.calls == 0
    assert marker not in error_text
    assert "input_value" not in error_text
    assert "unique evidence IDs" in error_text


@pytest.mark.asyncio
async def test_audit_and_resume_relationship_errors_are_sanitized() -> None:
    marker = "RELATIONSHIP_LEAK_MARKER"
    provider = NoCallProvider()
    server = create_server(TaskRelayService(provider))
    checkpoint = _artifact("codebuddy_checkpoint_2026-07-20.json")
    duplicate_evidence = {
        "evidence_id": checkpoint["evidence"][0]["evidence_id"],
        "content": marker,
        "source": "synthetic log",
    }
    audit = _artifact("codex_audit_2026-07-20.json")
    audit["checkpoint_id"] = "cp_0000000000000000"

    async with create_connected_server_and_client_session(server) as session:
        audit_result = await session.call_tool(
            "taskrelay_audit_checkpoint",
            {"checkpoint": checkpoint, "additional_evidence": [duplicate_evidence]},
        )
        resume_result = await session.call_tool(
            "taskrelay_create_resume_brief",
            {"checkpoint": checkpoint, "audit": audit, "continuation_context": marker},
        )

    for result in (audit_result, resume_result):
        error_text = _error_text(result)
        assert result.isError is True
        assert marker not in error_text
        assert "input_value" not in error_text
    assert provider.calls == 0
