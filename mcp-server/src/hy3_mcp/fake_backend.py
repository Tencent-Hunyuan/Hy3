# Copyright 2026 Tencent Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Deterministic offline stand-in for the Hy3 chat-completions endpoint.

The fake is an :class:`httpx.MockTransport` handler that speaks the exact
OpenAI wire format, so the production code path (the real ``openai``
AsyncOpenAI SDK — request assembly, timeouts, usage accounting) is shared
100% between offline and real mode; only the HTTP transport is swapped.

Routing: :mod:`hy3_mcp.hy3_client` prefixes every system prompt with a
``[hy3-mcp task=<name>]`` marker.  The handler dispatches on that marker to
one of five pure functions of the *user* message text, so identical inputs
always produce byte-identical replies (the backbone of the test suite).

Every fake reply starts with an explicit honesty banner::

    > OFFLINE DEMO MODE (fake Hy3 backend) -- deterministic canned analysis

and, for testability, echoes the forwarded ``chat_template_kwargs`` as a
trailing HTML comment (``<!-- effort=... -->``).  All output is pure ASCII.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Callable

import httpx

__all__ = ["build_fake_transport", "OFFLINE_BANNER"]

#: First line of every fake completion (tests and the demo GIF rely on it).
OFFLINE_BANNER = "> OFFLINE DEMO MODE (fake Hy3 backend) -- deterministic canned analysis"

_TASK_RE = re.compile(r"\[hy3-mcp task=([\w-]+)\]")
_CHUNK_RE = re.compile(r"^\[chunk (\d+) \| ([^\]]+)\]$", re.M)
_SOURCE_RE = re.compile(r"^\[source (\d+) \| ([^\]]+)\]$", re.M)


def _fake_review(user: str) -> str:
    """Canned code review: scans the submitted diff with tiny heuristics."""
    # Number lines relative to the diff body when the prompt marks it.
    body = user
    if "=== BEGIN DIFF ===" in user:
        body = user.split("=== BEGIN DIFF ===", 1)[1].split("=== END DIFF ===", 1)[0]
        body = body.strip("\n")
    findings: list[str] = []
    for i, line in enumerate(body.splitlines(), start=1):
        low = line.lower()
        if "password" in low or "secret" in low:
            findings.append(
                f"- **[security/high]** line {i}: possible hardcoded credential "
                f"(`{line.strip()[:60]}`). Move it to an environment variable or a secret store."
            )
        elif "eval(" in line or "== None" in line or "!= None" in line:
            findings.append(
                f"- **[correctness/medium]** line {i}: fragile construct "
                f"(`{line.strip()[:60]}`). Prefer `ast.literal_eval`/`is None`."
            )
        elif "TODO" in line or "FIXME" in line:
            findings.append(
                f"- **[maintainability/low]** line {i}: leftover TODO/FIXME marker."
            )
        elif len(line) > 120:
            findings.append(
                f"- **[style/low]** line {i}: line exceeds 120 characters ({len(line)})."
            )
    if not findings:
        findings.append("- No blocking issue found by the canned heuristics.")
    return "\n".join(
        [
            OFFLINE_BANNER,
            "",
            "## Code review (canned)",
            "",
            "Summary: reviewed the submitted change; findings below are ordered by severity.",
            "",
            *findings,
            "",
            "Recommendation: fix the high-severity findings before merging.",
        ]
    )


def _fake_docs(user: str) -> str:
    """Canned doc QA: answers from the first evidence chunk, with citation."""
    m = _CHUNK_RE.search(user)
    if m is None:
        return "\n".join(
            [
                OFFLINE_BANNER,
                "",
                "I could not find evidence chunks in the request, so I will not invent an answer.",
            ]
        )
    ref = m.group(2)
    tail = user[m.end():].strip()
    first_para = tail.split("\n\n")[0].strip().replace("\n", " ")
    return "\n".join(
        [
            OFFLINE_BANNER,
            "",
            "## Answer (grounded in the retrieved chunks)",
            "",
            f"According to the knowledge base: {first_para[:400]}",
            "",
            f"Citation: ({ref})",
        ]
    )


def _fake_data(user: str) -> str:
    """Canned data analysis: restates key numbers from the PROFILE JSON."""
    rows = "?"
    cols = "?"
    m = re.search(r"```json\n(.*?)\n```", user, re.S)
    if m is not None:
        try:
            profile = json.loads(m.group(1))
            rows = str(profile.get("rows", "?"))
            cols = str(len(profile.get("columns", [])))
        except (json.JSONDecodeError, AttributeError, TypeError):
            pass
    return "\n".join(
        [
            OFFLINE_BANNER,
            "",
            "## Data analysis (canned)",
            "",
            f"The dataset has {rows} rows and {cols} columns. "
            "Numeric columns look healthy; check the missing-value counts in the profile.",
            "",
            "Chart ideas:",
            "1. A bar chart comparing the main categorical column against the primary metric.",
            "2. A line or histogram view of the main numeric column to spot outliers.",
        ]
    )


def _fake_research(user: str) -> str:
    """Canned research synthesis: one bullet per [source N | ...] header."""
    bullets = [
        f"- Source {num} ({ref[:70]}): relevant evidence noted."
        for num, ref in _SOURCE_RE.findall(user)
    ]
    if not bullets:
        bullets.append("- No sources were provided; conclusions withheld (no fabrication).")
    return "\n".join(
        [
            OFFLINE_BANNER,
            "",
            "## Research notes (canned)",
            "",
            *bullets,
            "",
            "## Conclusion",
            "",
            "The collected sources are consistent; see the per-source notes above. "
            "Re-run against the real Hy3 backend for a full synthesis.",
        ]
    )


def _fake_generic(user: str) -> str:
    digest = hashlib.sha1(user.encode("utf-8", "replace")).hexdigest()[:8]
    return "\n".join(
        [
            OFFLINE_BANNER,
            "",
            f"Generic canned reply for request {digest}.",
        ]
    )


_DISPATCH: dict[str, Callable[[str], str]] = {
    "review": _fake_review,
    "docs": _fake_docs,
    "data": _fake_data,
    "research": _fake_research,
}


def _handle(request: httpx.Request) -> httpx.Response:
    if not request.url.path.endswith("/chat/completions"):
        return httpx.Response(404, json={"error": {"message": "unknown endpoint"}})

    payload = json.loads(request.content)
    messages = payload.get("messages", [])
    system = next((m["content"] for m in messages if m.get("role") == "system"), "")
    user = next(
        (m["content"] for m in reversed(messages) if m.get("role") == "user"), ""
    )

    task_match = _TASK_RE.search(system)
    task = task_match.group(1) if task_match else "generic"
    text = _DISPATCH.get(task, _fake_generic)(user)

    # Echo the forwarded chat_template_kwargs (reasoning_effort) so tests can
    # assert end-to-end forwarding without touching the wire format.
    kwargs = payload.get("chat_template_kwargs") or {}
    effort = kwargs.get("reasoning_effort")
    if effort is not None:
        text += f"\n\n<!-- effort={effort} -->"

    prompt_tokens = sum(len(str(m.get("content", ""))) for m in messages) // 4
    completion_tokens = len(text) // 4
    request_id = hashlib.sha1(request.content).hexdigest()[:12]

    body = {
        "id": f"chatcmpl-fake-{request_id}",
        "object": "chat.completion",
        "created": 1700000000,
        "model": payload.get("model", "hy3"),
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }
    return httpx.Response(200, json=body)


def build_fake_transport() -> httpx.MockTransport:
    """Return the mock HTTP transport implementing the fake Hy3 endpoint."""
    return httpx.MockTransport(_handle)
