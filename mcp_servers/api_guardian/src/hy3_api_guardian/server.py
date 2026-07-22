"""FastMCP stdio entrypoint exposing exactly three read-only Hy3 tools."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from . import __version__
from .errors import GuardianError
from .models import AuditResult, BreakingChangeResult, ContractTestResult
from .services import (
    audit_openapi_service,
    detect_breaking_changes_service,
    generate_contract_tests_service,
)
from .settings import Settings

mcp = FastMCP(
    name="Hy3 API Guardian",
    instructions=(
        "Read-only OpenAPI governance tools powered by Hy3. Provide file paths inside "
        "HY3_ALLOWED_ROOT or inline OpenAPI text. The server never modifies source files."
    ),
)
# FastMCP 1.x does not expose a public version constructor argument. Its low-level
# server does, so set it explicitly to report this package's version during MCP
# initialization instead of the installed SDK version.
mcp._mcp_server.version = __version__


def _safe_error(error: GuardianError) -> ValueError:
    return ValueError(str(error))


@mcp.tool(
    title="Audit OpenAPI contract",
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def audit_openapi(
    spec_path: Annotated[
        str | None,
        Field(description="Path to one OpenAPI 3.x JSON/YAML file inside HY3_ALLOWED_ROOT."),
    ] = None,
    spec_text: Annotated[
        str | None,
        Field(description="Inline OpenAPI 3.x JSON/YAML; use instead of spec_path."),
    ] = None,
    focus: Annotated[
        Literal["all", "security", "design", "reliability", "developer_experience"],
        Field(description="Primary audit perspective for Hy3; deterministic checks always run."),
    ] = "all",
) -> AuditResult:
    """Audit one OpenAPI contract with deterministic checks and grounded Hy3 analysis."""
    try:
        return await audit_openapi_service(
            spec_path=spec_path,
            spec_text=spec_text,
            focus=focus,
            settings=Settings.from_env(),
        )
    except GuardianError as exc:
        raise _safe_error(exc) from None


@mcp.tool(
    title="Detect breaking API changes",
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def detect_breaking_changes(
    old_spec_path: Annotated[
        str | None,
        Field(description="Path to the old OpenAPI 3.x file inside HY3_ALLOWED_ROOT."),
    ] = None,
    old_spec_text: Annotated[
        str | None,
        Field(description="Inline old OpenAPI 3.x document; use instead of old_spec_path."),
    ] = None,
    new_spec_path: Annotated[
        str | None,
        Field(description="Path to the new OpenAPI 3.x file inside HY3_ALLOWED_ROOT."),
    ] = None,
    new_spec_text: Annotated[
        str | None,
        Field(description="Inline new OpenAPI 3.x document; use instead of new_spec_path."),
    ] = None,
    include_compatible: Annotated[
        bool,
        Field(description="Include additive compatible changes in the returned change list."),
    ] = True,
) -> BreakingChangeResult:
    """Compare two OpenAPI contracts and explain breaking changes with Hy3."""
    try:
        return await detect_breaking_changes_service(
            old_spec_path=old_spec_path,
            old_spec_text=old_spec_text,
            new_spec_path=new_spec_path,
            new_spec_text=new_spec_text,
            include_compatible=include_compatible,
            settings=Settings.from_env(),
        )
    except GuardianError as exc:
        raise _safe_error(exc) from None


@mcp.tool(
    title="Generate API contract tests",
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def generate_contract_tests(
    spec_path: Annotated[
        str | None,
        Field(description="Path to one OpenAPI 3.x file inside HY3_ALLOWED_ROOT."),
    ] = None,
    spec_text: Annotated[
        str | None,
        Field(description="Inline OpenAPI 3.x JSON/YAML; use instead of spec_path."),
    ] = None,
    framework: Annotated[
        Literal["pytest", "jest"],
        Field(description="Contract-test framework for the generated source file."),
    ] = "pytest",
    selected_paths: Annotated[
        list[str] | None,
        Field(
            description=(
                "Optional path or 'METHOD /path' selectors. At most 20 matched operations "
                "are allowed."
            )
        ),
    ] = None,
) -> ContractTestResult:
    """Generate executable contract tests grounded in an OpenAPI contract using Hy3."""
    try:
        return await generate_contract_tests_service(
            spec_path=spec_path,
            spec_text=spec_text,
            framework=framework,
            selected_paths=selected_paths,
            settings=Settings.from_env(),
        )
    except GuardianError as exc:
        raise _safe_error(exc) from None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hy3 API Guardian MCP server")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate environment settings without starting the stdio server.",
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    if args.check:
        try:
            settings = Settings.from_env()
            settings.require_api_key()
        except GuardianError as exc:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
            raise SystemExit(1) from None
        print(json.dumps({"ok": True, **settings.safe_summary()}, ensure_ascii=False))
        return
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
