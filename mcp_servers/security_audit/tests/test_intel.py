"""Tests for synthesize_advisory: empty-vuln short-circuit, untrusted framing
of OSV data, high reasoning effort, and reply parsing.
"""

from __future__ import annotations

import json

import pytest

from hy3_security_mcp.framing import UNTRUSTED_NOTICE
from hy3_security_mcp.intel import render_vuln_intel_prompt, synthesize_advisory
from hy3_security_mcp.osv import OSVVulnerability
from hy3_security_mcp.schemas import FindingSeverity, VerdictParseError
from tests.fakes import FakeHy3Client


def _vuln(vuln_id: str = "GHSA-xxxx-xxxx-xxxx") -> OSVVulnerability:
    return OSVVulnerability(
        id=vuln_id,
        summary="Improper input validation",
        details="A crafted redirect can leak the Proxy-Authorization header.",
        aliases=["CVE-2023-12345"],
        severity=[{"type": "CVSS_V3", "score": "7.5"}],
        affected_summary="requests: >= 0, < 2.31.0",
    )


def _fake_report_reply(
    severity: str = "high",
    overall_priority: str = "high",
    summary: str = "发现 1 处高危漏洞",
) -> str:
    return json.dumps(
        {
            "advisories": [
                {
                    "vuln_id": "GHSA-xxxx-xxxx-xxxx",
                    "severity": severity,
                    "affected": "requests < 2.31.0",
                    "exploitability": "需要构造恶意重定向才能触发",
                    "remediation": "升级至 2.31.0 及以上版本",
                    "references": ["https://osv.dev/GHSA-xxxx-xxxx-xxxx"],
                }
            ],
            "summary": summary,
            "overall_priority": overall_priority,
        }
    )


class TestEmptyVulns:
    async def test_empty_list_returns_info_report_without_llm_call(self) -> None:
        fake = FakeHy3Client(replies=[])

        report = await synthesize_advisory([], client=fake)

        assert report.advisories == []
        assert report.summary == "未发现已知漏洞"
        assert report.overall_priority == FindingSeverity.INFO
        assert fake.calls == []


class TestNonEmptyVulns:
    async def test_reasoning_effort_is_high(self) -> None:
        fake = FakeHy3Client(replies=[_fake_report_reply()])

        await synthesize_advisory([_vuln()], client=fake)

        _, _, reasoning_effort = fake.calls[0]
        assert reasoning_effort == "high"

    async def test_user_message_contains_fenced_untrusted_vuln_data(self) -> None:
        fake = FakeHy3Client(replies=[_fake_report_reply()])

        await synthesize_advisory([_vuln()], client=fake)

        _, user, _ = fake.calls[0]
        assert "```" in user
        assert UNTRUSTED_NOTICE in user
        assert "GHSA-xxxx-xxxx-xxxx" in user
        assert "CVE-2023-12345" in user

    async def test_context_rendered_as_untrusted_section(self) -> None:
        fake = FakeHy3Client(replies=[_fake_report_reply()])

        await synthesize_advisory([_vuln()], client=fake, context="生产环境后端依赖,面向公网")

        _, user, _ = fake.calls[0]
        assert "## 使用场景" in user
        assert "生产环境后端依赖,面向公网" in user

    async def test_no_context_omits_scenario_section(self) -> None:
        fake = FakeHy3Client(replies=[_fake_report_reply()])

        await synthesize_advisory([_vuln()], client=fake)

        _, user, _ = fake.calls[0]
        assert "## 使用场景" not in user

    async def test_system_prompt_matches_render_vuln_intel_prompt(self) -> None:
        fake = FakeHy3Client(replies=[_fake_report_reply()])

        await synthesize_advisory([_vuln()], client=fake)

        system, _, _ = fake.calls[0]
        assert system == render_vuln_intel_prompt()

    async def test_malformed_reply_raises_verdict_parse_error(self) -> None:
        fake = FakeHy3Client(replies=["not json at all"])

        with pytest.raises(VerdictParseError):
            await synthesize_advisory([_vuln()], client=fake)

    async def test_valid_reply_round_trips_severity_and_priority(self) -> None:
        fake = FakeHy3Client(
            replies=[_fake_report_reply(severity="critical", overall_priority="critical")]
        )

        report = await synthesize_advisory([_vuln()], client=fake)

        assert len(report.advisories) == 1
        assert report.advisories[0].severity == FindingSeverity.CRITICAL
        assert report.advisories[0].vuln_id == "GHSA-xxxx-xxxx-xxxx"
        assert report.overall_priority == FindingSeverity.CRITICAL


class TestVulnCountCap:
    """A package with hundreds of known vulns must not blow up the
    high-effort prompt: at most N=50 vulns are serialized, and any truncation
    is surfaced in the prompt rather than silently dropped."""

    async def test_more_than_cap_vulns_are_capped_and_truncation_is_surfaced(self) -> None:
        vulns = [_vuln(f"GHSA-{i:04d}") for i in range(60)]
        fake = FakeHy3Client(replies=[_fake_report_reply()])

        await synthesize_advisory(vulns, client=fake)

        _, user, _ = fake.calls[0]
        assert "GHSA-0000" in user
        assert "GHSA-0049" in user
        assert "GHSA-0050" not in user
        assert "GHSA-0059" not in user
        # The 10 omitted vulns must be surfaced (report input or log), not
        # silently dropped.
        assert "10" in user

    async def test_at_or_below_cap_is_not_flagged_as_truncated(self) -> None:
        vulns = [_vuln(f"GHSA-{i:04d}") for i in range(50)]
        fake = FakeHy3Client(replies=[_fake_report_reply()])

        await synthesize_advisory(vulns, client=fake)

        _, user, _ = fake.calls[0]
        assert "GHSA-0000" in user
        assert "GHSA-0049" in user
        assert "omitted" not in user
        assert "未展示" not in user
