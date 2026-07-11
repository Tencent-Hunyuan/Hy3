"""Tests for triage_secrets: empty-candidate short-circuit, untrusted framing
of the (already-redacted) candidate list, no_think reasoning effort, and
reply parsing.
"""

from __future__ import annotations

import json

import pytest

from hy3_security_mcp.framing import UNTRUSTED_NOTICE
from hy3_security_mcp.scan import render_secret_triage_prompt, triage_secrets
from hy3_security_mcp.schemas import FindingSeverity, VerdictParseError
from hy3_security_mcp.secrets import SecretCandidate, scan_text
from tests.fakes import FakeHy3Client


def _fake_report_reply(
    is_true_positive: bool = True,
    severity: str = "high",
    summary: str = "发现 1 处疑似真实密钥",
) -> str:
    return json.dumps(
        {
            "secrets": [
                {
                    "line": 2,
                    "kind": "OPENAI_KEY",
                    "is_true_positive": is_true_positive,
                    "severity": severity,
                    "rationale": "疑似真实的 OpenAI API 密钥",
                    "remediation": "立即轮换密钥并移入密管服务",
                }
            ],
            "summary": summary,
        }
    )


class TestEmptyCandidates:
    async def test_empty_list_returns_empty_report_without_llm_call(self) -> None:
        fake = FakeHy3Client(replies=[])

        report = await triage_secrets([], client=fake)

        assert report.secrets == []
        assert report.summary
        assert fake.calls == []


class TestNonEmptyCandidates:
    _CANDIDATES = [
        SecretCandidate(
            kind="OPENAI_KEY",
            line=2,
            column=18,
            snippet='OPENAI_API_KEY = "***REDACTED-OPENAI_KEY***"',
        )
    ]

    async def test_reasoning_effort_is_no_think(self) -> None:
        fake = FakeHy3Client(replies=[_fake_report_reply()])

        await triage_secrets(self._CANDIDATES, client=fake)

        _, _, reasoning_effort = fake.calls[0]
        assert reasoning_effort == "no_think"

    async def test_user_message_contains_fenced_untrusted_candidate_list(self) -> None:
        fake = FakeHy3Client(replies=[_fake_report_reply()])

        await triage_secrets(self._CANDIDATES, client=fake)

        _, user, _ = fake.calls[0]
        assert "```" in user
        assert UNTRUSTED_NOTICE in user
        assert "OPENAI_KEY" in user
        assert "***REDACTED-OPENAI_KEY***" in user

    async def test_raw_planted_secret_absent_from_user_message(self) -> None:
        # Exercise the real scanner so the candidate's snippet is genuinely
        # redact()-produced, then prove the raw secret never reaches the
        # prompt via triage_secrets either.
        secret = "sk-abcdefghijklmnopqrstuvwx1234"
        candidates = scan_text(f'OPENAI_API_KEY = "{secret}"\n')
        fake = FakeHy3Client(replies=[_fake_report_reply()])

        await triage_secrets(candidates, client=fake)

        _, user, _ = fake.calls[0]
        assert secret not in user
        assert "***REDACTED-OPENAI_KEY***" in user

    async def test_system_prompt_matches_render_secret_triage_prompt(self) -> None:
        fake = FakeHy3Client(replies=[_fake_report_reply()])

        await triage_secrets(self._CANDIDATES, client=fake)

        system, _, _ = fake.calls[0]
        assert system == render_secret_triage_prompt()

    async def test_malformed_reply_raises_verdict_parse_error(self) -> None:
        fake = FakeHy3Client(replies=["not json at all"])

        with pytest.raises(VerdictParseError):
            await triage_secrets(self._CANDIDATES, client=fake)

    async def test_valid_reply_round_trips_severity_and_true_positive(self) -> None:
        fake = FakeHy3Client(replies=[_fake_report_reply(severity="critical")])

        report = await triage_secrets(self._CANDIDATES, client=fake)

        assert len(report.secrets) == 1
        assert report.secrets[0].severity == FindingSeverity.CRITICAL
        assert report.secrets[0].is_true_positive is True
        assert report.secrets[0].line == 2
        assert report.secrets[0].kind == "OPENAI_KEY"

    async def test_false_positive_reply_round_trips(self) -> None:
        fake = FakeHy3Client(replies=[_fake_report_reply(is_true_positive=False, severity="info")])

        report = await triage_secrets(self._CANDIDATES, client=fake)

        assert report.secrets[0].is_true_positive is False
        assert report.secrets[0].severity == FindingSeverity.INFO
