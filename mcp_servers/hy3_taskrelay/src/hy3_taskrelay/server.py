"""MCP stdio surface for Hy3 TaskRelay."""

from __future__ import annotations

import json
from typing import Annotated, Any, cast

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.fastmcp.tools import Tool
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from pydantic import BaseModel, Field, ValidationError

from hy3_taskrelay.config import ConfigError, Settings
from hy3_taskrelay.errors import TaskRelayError
from hy3_taskrelay.hy3_client import Hy3Client
from hy3_taskrelay.schemas import (
    AuditCheckpointInput,
    AuditResult,
    Checkpoint,
    CreateCheckpointInput,
    CreateResumeBriefInput,
    Evidence,
    ResumeBrief,
    ShortText,
)
from hy3_taskrelay.service import TaskRelayService

TOOL_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)


def _safe_validation_message(tool_name: str) -> str:
    return (
        f"Invalid {tool_name} input. Check the documented field types and limits, unique "
        "evidence IDs, content-derived IDs, and checkpoint/audit consistency."
    )


_SAFE_FIELD_NAMES = {
    "additional_evidence",
    "audit",
    "blockers",
    "category",
    "checkpoint",
    "checkpoint_id",
    "concise_context",
    "constraints",
    "content",
    "continuation_context",
    "decisions",
    "do_not",
    "evidence",
    "evidence_id",
    "evidence_ids",
    "finding_id",
    "findings",
    "goal",
    "next_steps",
    "open_questions",
    "overall_status",
    "priority",
    "question",
    "recommendation",
    "resume_id",
    "schema_version",
    "session_material",
    "severity",
    "source",
    "summary",
    "text",
    "validation",
    "verification",
}


def _safe_validation_location(error: ValidationError) -> str | None:
    for detail in error.errors(include_url=False, include_context=False, include_input=False):
        location = detail.get("loc", ())
        if not location or not any(isinstance(part, str) for part in location):
            continue
        if all(
            (isinstance(part, str) and part in _SAFE_FIELD_NAMES)
            or (isinstance(part, int) and part >= 0)
            for part in location
        ):
            return ".".join(str(part) for part in location)
    return None


class _SafeTool(Tool):
    """Prevent SDK argument-validation failures from echoing caller input."""

    async def run(self, *args: Any, **kwargs: Any) -> Any:
        try:
            return await super().run(*args, **kwargs)
        except ToolError as error:
            cause = error.__cause__
            if isinstance(cause, ValidationError):
                message = _safe_validation_message(self.name)
                if location := _safe_validation_location(cause):
                    message = f"{message} First invalid field: {location}."
                raise ToolError(message) from None
            if isinstance(cause, ToolError):
                raise ToolError(str(cause)) from None
            if cause is not None:
                raise ToolError(
                    f"{self.name} failed without exposing internal details. Retry the call or "
                    "check the documented configuration."
                ) from None
            raise


def _tool_result(model: BaseModel, summary: str) -> CallToolResult:
    return CallToolResult(
        content=[
            TextContent(type="text", text=summary),
            TextContent(
                type="text",
                text=json.dumps(
                    model.model_dump(mode="json"),
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            ),
        ],
        structuredContent=model.model_dump(mode="json"),
    )


def create_server(service: TaskRelayService | None = None) -> FastMCP:
    """Build the server; a service may be injected at the external-API boundary for tests."""

    def get_service() -> TaskRelayService:
        if service is not None:
            return service
        settings = Settings.from_env()
        secret = settings.api_key.get_secret_value()
        return TaskRelayService(Hy3Client(settings), secret_values=(secret,))

    async def taskrelay_create_checkpoint(
        goal: Annotated[
            str, Field(min_length=1, max_length=2_000, description="Task outcome to preserve")
        ],
        session_material: Annotated[
            str,
            Field(
                min_length=1,
                max_length=12_000,
                description="Relevant material from the interrupted session",
            ),
        ],
        evidence: Annotated[
            list[Evidence],
            Field(
                min_length=1,
                max_length=50,
                description="Evidence items with caller-stable ev_ identifiers",
            ),
        ],
        constraints: Annotated[
            tuple[ShortText, ...],
            Field(max_length=30, description="Explicit constraints to retain"),
        ] = (),
        decisions: Annotated[
            tuple[ShortText, ...], Field(max_length=30, description="Decisions already made")
        ] = (),
    ) -> Checkpoint:
        try:
            result = await get_service().create_checkpoint(
                CreateCheckpointInput(
                    goal=goal,
                    session_material=session_material,
                    constraints=list(constraints),
                    decisions=list(decisions),
                    evidence=evidence,
                )
            )
        except (ConfigError, TaskRelayError) as error:
            raise ToolError(str(error)) from None
        return cast(
            Checkpoint,
            _tool_result(
                result,
                f"Created checkpoint {result.checkpoint_id} with "
                f"{len(result.confirmed_facts)} grounded facts and "
                f"{len(result.next_steps)} next steps.",
            ),
        )

    async def taskrelay_audit_checkpoint(
        checkpoint: Annotated[Checkpoint, Field(description="Portable checkpoint to audit")],
        additional_evidence: Annotated[
            tuple[Evidence, ...],
            Field(max_length=20, description="Optional evidence learned after checkpoint creation"),
        ] = (),
    ) -> AuditResult:
        try:
            result = await get_service().audit_checkpoint(
                AuditCheckpointInput(
                    checkpoint=checkpoint,
                    additional_evidence=list(additional_evidence),
                )
            )
        except (ConfigError, TaskRelayError) as error:
            raise ToolError(str(error)) from None
        return cast(
            AuditResult,
            _tool_result(
                result,
                f"Audited checkpoint {result.checkpoint_id}: {result.overall_status}; "
                f"{len(result.findings)} findings.",
            ),
        )

    async def taskrelay_create_resume_brief(
        checkpoint: Annotated[Checkpoint, Field(description="Portable checkpoint to resume")],
        audit: Annotated[AuditResult, Field(description="Audit result for the same checkpoint")],
        additional_evidence: Annotated[
            tuple[Evidence, ...],
            Field(max_length=20, description="Optional evidence learned after the audit"),
        ] = (),
        continuation_context: Annotated[
            str,
            Field(
                max_length=4_000,
                description="Optional context about the client or session continuing the task",
            ),
        ] = "",
    ) -> ResumeBrief:
        try:
            result = await get_service().create_resume_brief(
                CreateResumeBriefInput(
                    checkpoint=checkpoint,
                    audit=audit,
                    additional_evidence=list(additional_evidence),
                    continuation_context=continuation_context,
                )
            )
        except (ConfigError, TaskRelayError) as error:
            raise ToolError(str(error)) from None
        return cast(
            ResumeBrief,
            _tool_result(
                result,
                f"Created resume brief {result.resume_id} for {result.checkpoint_id} with "
                f"{len(result.next_steps)} prioritized steps.",
            ),
        )

    tools = [
        _SafeTool.from_function(
            taskrelay_create_checkpoint,
            name="taskrelay_create_checkpoint",
            description=(
                "Turn explicit task material into a portable, evidence-grounded checkpoint for "
                "another session or MCP client. The caller remains responsible for saving the "
                "returned object."
            ),
            annotations=TOOL_ANNOTATIONS,
            structured_output=True,
        ),
        _SafeTool.from_function(
            taskrelay_audit_checkpoint,
            name="taskrelay_audit_checkpoint",
            description=(
                "Audit a TaskRelay checkpoint for contradictions, omitted constraints, stale "
                "assumptions, and unsupported claims using only supplied evidence."
            ),
            annotations=TOOL_ANNOTATIONS,
            structured_output=True,
        ),
        _SafeTool.from_function(
            taskrelay_create_resume_brief,
            name="taskrelay_create_resume_brief",
            description=(
                "Create a concise continuation brief with prioritized steps, validation gates, "
                "blockers, and prohibited actions from a checkpoint and its audit."
            ),
            annotations=TOOL_ANNOTATIONS,
            structured_output=True,
        ),
    ]
    return FastMCP(
        "Hy3 TaskRelay",
        instructions=(
            "Create, audit, and resume caller-owned long-task checkpoints. The server is stateless "
            "and does not persist files or execute commands."
        ),
        tools=tools,
        log_level="WARNING",
    )


def main() -> None:
    """Run the local stdio MCP server."""

    create_server().run(transport="stdio")
