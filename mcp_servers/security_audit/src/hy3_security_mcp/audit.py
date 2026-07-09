"""Wires the policy engine (fast path + LLM) into a single audit entrypoint.

``audit_command_verdict`` is the one place that decides whether a shell
command needs an LLM call at all: ``evaluate_fast`` runs first and, on a hit,
short-circuits before any network/LLM interaction. Otherwise the command (and
optional context) is framed as untrusted data and handed to Hy3 for
adjudication.
"""

from __future__ import annotations

import functools

from hy3_security_mcp.framing import UNTRUSTED_NOTICE, fenced
from hy3_security_mcp.hy3_client import Hy3CompletionClient
from hy3_security_mcp.policy import evaluate_fast, render_system_prompt
from hy3_security_mcp.schemas import AuditVerdict, parse_verdict


@functools.cache
def _system_prompt() -> str:
    """Cache the rendered system prompt — render_system_prompt() is deterministic."""
    return render_system_prompt()


def _build_user_message(command: str, context: str | None) -> str:
    sections = [
        "## 待审计命令",
        UNTRUSTED_NOTICE,
        fenced(command),
    ]
    if context is not None:
        sections += [
            "## 场景上下文",
            UNTRUSTED_NOTICE,
            fenced(context),
        ]
    return "\n".join(sections)


async def audit_command_verdict(
    command: str, *, client: Hy3CompletionClient, context: str | None = None
) -> AuditVerdict:
    """Audit one shell command: deterministic fast path first, else ask Hy3.

    Raises VerdictParseError if the LLM reply cannot be parsed into a valid
    AuditVerdict — this is intentional fail-fast behavior; callers (the MCP
    tool layer) surface it as a tool error rather than silently guessing.
    """
    fast_verdict = evaluate_fast(command)
    if fast_verdict is not None:
        return fast_verdict

    user_message = _build_user_message(command, context)
    reply = await client.complete(
        system=_system_prompt(), user=user_message, reasoning_effort="no_think"
    )
    return parse_verdict(reply, source="llm")
