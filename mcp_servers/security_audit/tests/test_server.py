"""Tests for the FastMCP stdio server: tool registration and in-memory calls.

Uses mcp.shared.memory.create_connected_server_and_client_session — the SDK's
in-memory transport helper — against build_server(fake)._mcp_server. No
subprocess is spawned; this exercises the real MCP protocol (list_tools,
call_tool) over in-process streams.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
from mcp.shared.memory import create_connected_server_and_client_session
from mcp.types import CallToolResult, TextContent

from hy3_security_mcp.osv import OSVClient
from hy3_security_mcp.server import _gather_package_vulns, build_server, main
from tests.conftest import run_git
from tests.fakes import FakeHy3Client


def _osv_client(handler: Callable[[httpx.Request], httpx.Response]) -> OSVClient:
    transport = httpx.MockTransport(handler)
    return OSVClient(http_client=httpx.AsyncClient(transport=transport))


def _is_cjk(text: str) -> bool:
    return any("一" <= ch <= "鿿" for ch in text)


def _content_to_dict(result: CallToolResult) -> dict[str, Any]:
    (block,) = result.content
    assert isinstance(block, TextContent)
    return json.loads(block.text)


class TestEntryPoint:
    def test_main_is_callable(self) -> None:
        assert callable(main)


class TestListTools:
    async def test_exactly_four_tools(self) -> None:
        fake = FakeHy3Client(replies=[])
        server = build_server(fake)

        async with create_connected_server_and_client_session(server._mcp_server) as session:
            result = await session.list_tools()

        assert {tool.name for tool in result.tools} == {
            "audit_command",
            "review_diff",
            "scan_secrets",
            "vuln_intel",
        }

    async def test_all_tool_descriptions_non_empty_and_bilingual(self) -> None:
        fake = FakeHy3Client(replies=[])
        server = build_server(fake)

        async with create_connected_server_and_client_session(server._mcp_server) as session:
            result = await session.list_tools()

        for tool in result.tools:
            assert tool.description
            assert _is_cjk(tool.description), f"{tool.name}: description should contain Chinese"

    async def test_audit_command_description_mentions_audit_in_english(self) -> None:
        fake = FakeHy3Client(replies=[])
        server = build_server(fake)

        async with create_connected_server_and_client_session(server._mcp_server) as session:
            result = await session.list_tools()

        by_name = {tool.name: tool for tool in result.tools}
        description = by_name["audit_command"].description
        assert description is not None
        assert "audit" in description.lower()

    async def test_review_diff_description_mentions_review_or_diff_in_english(self) -> None:
        fake = FakeHy3Client(replies=[])
        server = build_server(fake)

        async with create_connected_server_and_client_session(server._mcp_server) as session:
            result = await session.list_tools()

        by_name = {tool.name: tool for tool in result.tools}
        description = by_name["review_diff"].description
        assert description is not None
        description = description.lower()
        assert "review" in description or "diff" in description

    async def test_input_schema_has_command_required_and_context_optional(self) -> None:
        fake = FakeHy3Client(replies=[])
        server = build_server(fake)

        async with create_connected_server_and_client_session(server._mcp_server) as session:
            result = await session.list_tools()

        by_name = {tool.name: tool for tool in result.tools}
        schema = by_name["audit_command"].inputSchema
        assert schema["required"] == ["command"]
        assert schema["properties"]["command"]["type"] == "string"
        assert "context" in schema["properties"]
        assert "context" not in schema["required"]

    async def test_review_diff_input_schema_has_no_required_fields(self) -> None:
        fake = FakeHy3Client(replies=[])
        server = build_server(fake)

        async with create_connected_server_and_client_session(server._mcp_server) as session:
            result = await session.list_tools()

        by_name = {tool.name: tool for tool in result.tools}
        schema = by_name["review_diff"].inputSchema
        assert not schema.get("required")
        for prop in ("repo_path", "staged", "ref_range", "focus"):
            assert prop in schema["properties"]

    async def test_scan_secrets_input_schema_has_no_required_fields(self) -> None:
        fake = FakeHy3Client(replies=[])
        server = build_server(fake)

        async with create_connected_server_and_client_session(server._mcp_server) as session:
            result = await session.list_tools()

        by_name = {tool.name: tool for tool in result.tools}
        schema = by_name["scan_secrets"].inputSchema
        assert not schema.get("required")
        for prop in ("path", "text"):
            assert prop in schema["properties"]

    async def test_scan_secrets_description_mentions_secret_or_scan_in_english(self) -> None:
        fake = FakeHy3Client(replies=[])
        server = build_server(fake)

        async with create_connected_server_and_client_session(server._mcp_server) as session:
            result = await session.list_tools()

        by_name = {tool.name: tool for tool in result.tools}
        description = by_name["scan_secrets"].description
        assert description is not None
        description = description.lower()
        assert "secret" in description or "scan" in description

    async def test_vuln_intel_input_schema_has_no_required_fields(self) -> None:
        fake = FakeHy3Client(replies=[])
        server = build_server(fake)

        async with create_connected_server_and_client_session(server._mcp_server) as session:
            result = await session.list_tools()

        by_name = {tool.name: tool for tool in result.tools}
        schema = by_name["vuln_intel"].inputSchema
        assert not schema.get("required")
        for prop in ("packages", "vuln_ids", "context"):
            assert prop in schema["properties"]

    async def test_vuln_intel_description_mentions_vuln_in_english(self) -> None:
        fake = FakeHy3Client(replies=[])
        server = build_server(fake)

        async with create_connected_server_and_client_session(server._mcp_server) as session:
            result = await session.list_tools()

        by_name = {tool.name: tool for tool in result.tools}
        description = by_name["vuln_intel"].description
        assert description is not None
        assert "vuln" in description.lower()


class TestCallTool:
    async def test_catastrophic_command_returns_fast_path_deny(self) -> None:
        fake = FakeHy3Client(replies=[])
        server = build_server(fake)

        async with create_connected_server_and_client_session(server._mcp_server) as session:
            result = await session.call_tool("audit_command", {"command": "rm -rf /"})

        payload = _content_to_dict(result)
        assert payload["level"] == "deny"
        assert payload["source"] == "fast_path"
        assert fake.calls == []

    async def test_normal_command_returns_llm_verdict(self) -> None:
        fake_reply = json.dumps(
            {
                "level": "confirm",
                "category": "sensitive_file",
                "rationale": "读取敏感文件,需人工确认",
                "safer_alternative": None,
            }
        )
        fake = FakeHy3Client(replies=[fake_reply])
        server = build_server(fake)

        async with create_connected_server_and_client_session(server._mcp_server) as session:
            result = await session.call_tool("audit_command", {"command": "cat ~/.ssh/id_rsa"})

        payload = _content_to_dict(result)
        assert payload["level"] == "confirm"
        assert payload["source"] == "llm"


class TestCallToolReviewDiff:
    async def test_staged_vulnerable_change_returns_dict_with_findings_list(
        self, git_repo: Path
    ) -> None:
        (git_repo / "app.py").write_text("import os\nprint('hi')\n")
        run_git(["add", "-A"], git_repo)
        run_git(["commit", "-m", "initial"], git_repo)

        (git_repo / "app.py").write_text("import os\nos.system(request.args['cmd'])\nprint('hi')\n")
        run_git(["add", "-A"], git_repo)

        fake_reply = json.dumps(
            {
                "findings": [
                    {
                        "severity": "critical",
                        "title": "命令注入",
                        "file": "app.py",
                        "line": 2,
                        "weakness": "命令注入",
                        "detail": "os.system 直接执行未经校验的用户输入",
                        "fix_suggestion": "改用参数化调用,避免拼接 shell 命令",
                    }
                ],
                "summary": "发现 1 处命令注入风险",
            }
        )
        fake = FakeHy3Client(replies=[fake_reply])
        server = build_server(fake)

        async with create_connected_server_and_client_session(server._mcp_server) as session:
            result = await session.call_tool(
                "review_diff", {"repo_path": str(git_repo), "staged": True}
            )

        payload = _content_to_dict(result)
        assert isinstance(payload["findings"], list)
        assert len(payload["findings"]) == 1
        assert payload["findings"][0]["weakness"] == "命令注入"
        assert payload["findings"][0]["severity"] == "critical"

        _, user, reasoning_effort = fake.calls[0]
        assert reasoning_effort == "high"
        assert "os.system" in user

    async def test_no_diff_returns_empty_findings_without_llm_call(self, git_repo: Path) -> None:
        (git_repo / "app.py").write_text("print('hi')\n")
        run_git(["add", "-A"], git_repo)
        run_git(["commit", "-m", "initial"], git_repo)

        fake = FakeHy3Client(replies=[])
        server = build_server(fake)

        async with create_connected_server_and_client_session(server._mcp_server) as session:
            result = await session.call_tool("review_diff", {"repo_path": str(git_repo)})

        payload = _content_to_dict(result)
        assert payload["findings"] == []
        assert fake.calls == []


class TestCallToolScanSecrets:
    async def test_text_with_planted_secret_returns_dict_with_secrets(self) -> None:
        secret = "sk-abcdefghijklmnopqrstuvwx1234"
        text = f'OPENAI_API_KEY = "{secret}"\nprint("hi")\n'
        fake_reply = json.dumps(
            {
                "secrets": [
                    {
                        "line": 1,
                        "kind": "OPENAI_KEY",
                        "is_true_positive": True,
                        "severity": "high",
                        "rationale": "疑似真实的 OpenAI API 密钥",
                        "remediation": "立即轮换密钥并移入密管服务",
                    }
                ],
                "summary": "发现 1 处疑似真实密钥",
            }
        )
        fake = FakeHy3Client(replies=[fake_reply])
        server = build_server(fake)

        async with create_connected_server_and_client_session(server._mcp_server) as session:
            result = await session.call_tool("scan_secrets", {"text": text})

        payload = _content_to_dict(result)
        assert isinstance(payload["secrets"], list)
        assert len(payload["secrets"]) == 1
        assert payload["secrets"][0]["kind"] == "OPENAI_KEY"

        # Non-negotiable: the raw planted secret never appears anywhere in
        # the tool's output, nor in what was sent to the LLM.
        (block,) = result.content
        assert isinstance(block, TextContent)
        assert secret not in block.text
        _, user, reasoning_effort = fake.calls[0]
        assert secret not in user
        assert reasoning_effort == "no_think"

    async def test_empty_candidates_returns_empty_secrets_without_llm_call(self) -> None:
        fake = FakeHy3Client(replies=[])
        server = build_server(fake)

        async with create_connected_server_and_client_session(server._mcp_server) as session:
            result = await session.call_tool("scan_secrets", {"text": "plain safe text\n"})

        payload = _content_to_dict(result)
        assert payload["secrets"] == []
        assert fake.calls == []

    async def test_path_reads_file_and_scans_it(self, tmp_path: Path) -> None:
        secret = "AKIAIOSFODNN7EXAMPLE"
        file_path = tmp_path / "config.py"
        file_path.write_text(f'aws_key = "{secret}"\n')

        fake_reply = json.dumps(
            {
                "secrets": [
                    {
                        "line": 1,
                        "kind": "AWS_ACCESS_KEY",
                        "is_true_positive": True,
                        "severity": "critical",
                        "rationale": "疑似真实的 AWS Access Key",
                        "remediation": "立即在 AWS IAM 中吊销并轮换",
                    }
                ],
                "summary": "发现 1 处疑似真实密钥",
            }
        )
        fake = FakeHy3Client(replies=[fake_reply])
        server = build_server(fake)

        async with create_connected_server_and_client_session(server._mcp_server) as session:
            result = await session.call_tool("scan_secrets", {"path": str(file_path)})

        payload = _content_to_dict(result)
        assert payload["secrets"][0]["kind"] == "AWS_ACCESS_KEY"
        _, user, _ = fake.calls[0]
        assert secret not in user

    async def test_both_path_and_text_is_a_tool_error(self, tmp_path: Path) -> None:
        file_path = tmp_path / "f.txt"
        file_path.write_text("hello\n")
        fake = FakeHy3Client(replies=[])
        server = build_server(fake)

        async with create_connected_server_and_client_session(server._mcp_server) as session:
            result = await session.call_tool(
                "scan_secrets", {"path": str(file_path), "text": "hello"}
            )

        assert result.isError is True
        assert fake.calls == []

    async def test_neither_path_nor_text_is_a_tool_error(self) -> None:
        fake = FakeHy3Client(replies=[])
        server = build_server(fake)

        async with create_connected_server_and_client_session(server._mcp_server) as session:
            result = await session.call_tool("scan_secrets", {})

        assert result.isError is True
        assert fake.calls == []

    async def test_co_located_entropy_secret_never_leaks_through_full_tool_path(self) -> None:
        # A realistic inline AWS access-key-id + secret pair: the id is a
        # known regex shape (AWS_ACCESS_KEY), but the secret half matches no
        # CREDENTIAL_PATTERNS shape and can only be masked by the entropy
        # pass. Both must be absent from the LLM prompt AND the tool output.
        aws_secret = "wJalrXUtnFEMIbKR7MDENGbPxRfiCYEXAMPLEKEY"
        text = f'aws = "AKIAIOSFODNN7EXAMPLE:{aws_secret}"\n'
        fake_reply = json.dumps(
            {
                "secrets": [
                    {
                        "line": 1,
                        "kind": "AWS_ACCESS_KEY",
                        "is_true_positive": True,
                        "severity": "critical",
                        "rationale": "疑似真实的 AWS Access Key 及配对密钥",
                        "remediation": "立即在 AWS IAM 中吊销并轮换",
                    }
                ],
                "summary": "发现 1 处疑似真实密钥",
            }
        )
        fake = FakeHy3Client(replies=[fake_reply])
        server = build_server(fake)

        async with create_connected_server_and_client_session(server._mcp_server) as session:
            result = await session.call_tool("scan_secrets", {"text": text})

        (block,) = result.content
        assert isinstance(block, TextContent)
        assert aws_secret not in block.text

        _, user, _ = fake.calls[0]
        assert aws_secret not in user


class TestGatherPackageVulns:
    """_gather_package_vulns is the tool's package-gathering step: a
    malformed entry must raise a descriptive ValueError naming the missing
    required key, not a bare KeyError, so a judge passing a bad dict gets a
    clear tool error instead of an opaque `'name'` repr."""

    def _osv(self) -> OSVClient:
        def handler(request: httpx.Request) -> httpx.Response:
            raise AssertionError("OSV.dev should not be called")

        return _osv_client(handler)

    async def test_missing_name_key_raises_value_error_naming_it(self) -> None:
        with pytest.raises(ValueError, match="name"):
            await _gather_package_vulns(self._osv(), [{"ecosystem": "PyPI"}])

    async def test_missing_ecosystem_key_raises_value_error_naming_it(self) -> None:
        with pytest.raises(ValueError, match="ecosystem"):
            await _gather_package_vulns(self._osv(), [{"name": "requests"}])


class TestCallToolVulnIntel:
    async def test_package_query_returns_dict_with_advisories(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/v1/query"
            assert json.loads(request.content) == {
                "package": {"name": "requests", "ecosystem": "PyPI"}
            }
            return httpx.Response(
                200,
                json={
                    "vulns": [
                        {
                            "id": "GHSA-xxxx-xxxx-xxxx",
                            "summary": "Improper input validation",
                            "aliases": ["CVE-2023-12345"],
                            "severity": [{"type": "CVSS_V3", "score": "7.5"}],
                        }
                    ]
                },
            )

        fake_reply = json.dumps(
            {
                "advisories": [
                    {
                        "vuln_id": "GHSA-xxxx-xxxx-xxxx",
                        "severity": "high",
                        "affected": "requests < 2.31.0",
                        "exploitability": "需要构造恶意重定向才能触发",
                        "remediation": "升级至 2.31.0 及以上版本",
                        "references": [],
                    }
                ],
                "summary": "发现 1 处高危漏洞",
                "overall_priority": "high",
            }
        )
        fake = FakeHy3Client(replies=[fake_reply])
        server = build_server(fake, osv_client=_osv_client(handler))

        async with create_connected_server_and_client_session(server._mcp_server) as session:
            result = await session.call_tool(
                "vuln_intel", {"packages": [{"name": "requests", "ecosystem": "PyPI"}]}
            )

        payload = _content_to_dict(result)
        assert isinstance(payload["advisories"], list)
        assert len(payload["advisories"]) == 1
        assert payload["advisories"][0]["vuln_id"] == "GHSA-xxxx-xxxx-xxxx"

        _, user, reasoning_effort = fake.calls[0]
        assert reasoning_effort == "high"
        assert "GHSA-xxxx-xxxx-xxxx" in user

    async def test_vuln_id_query_returns_dict_with_advisories(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/v1/vulns/CVE-2023-12345"
            return httpx.Response(
                200,
                json={
                    "id": "CVE-2023-12345",
                    "summary": "Improper input validation",
                    "aliases": [],
                    "severity": [],
                },
            )

        fake_reply = json.dumps(
            {
                "advisories": [
                    {
                        "vuln_id": "CVE-2023-12345",
                        "severity": "medium",
                        "affected": "见漏洞详情",
                        "exploitability": "需要特定前置条件",
                        "remediation": "关注上游修复版本",
                        "references": [],
                    }
                ],
                "summary": "发现 1 处中危漏洞",
                "overall_priority": "medium",
            }
        )
        fake = FakeHy3Client(replies=[fake_reply])
        server = build_server(fake, osv_client=_osv_client(handler))

        async with create_connected_server_and_client_session(server._mcp_server) as session:
            result = await session.call_tool("vuln_intel", {"vuln_ids": ["CVE-2023-12345"]})

        payload = _content_to_dict(result)
        assert payload["advisories"][0]["vuln_id"] == "CVE-2023-12345"

    async def test_one_failing_vuln_id_yields_partial_results_not_total_failure(self) -> None:
        # A single bad/404 id must NOT sink the whole batch: valid advisories
        # for the other ids must still be returned, with the failure surfaced
        # in a per-id error list instead of turning the call into a tool error.
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/v1/vulns/CVE-2023-00001":
                return httpx.Response(
                    200,
                    json={
                        "id": "CVE-2023-00001",
                        "summary": "Improper input validation",
                        "aliases": [],
                        "severity": [],
                    },
                )
            return httpx.Response(404, text="not found")

        fake_reply = json.dumps(
            {
                "advisories": [
                    {
                        "vuln_id": "CVE-2023-00001",
                        "severity": "medium",
                        "affected": "见漏洞详情",
                        "exploitability": "需要特定前置条件",
                        "remediation": "关注上游修复版本",
                        "references": [],
                    }
                ],
                "summary": "发现 1 处中危漏洞",
                "overall_priority": "medium",
            }
        )
        fake = FakeHy3Client(replies=[fake_reply])
        server = build_server(fake, osv_client=_osv_client(handler))

        async with create_connected_server_and_client_session(server._mcp_server) as session:
            result = await session.call_tool(
                "vuln_intel", {"vuln_ids": ["CVE-2023-00001", "CVE-DOES-NOT-EXIST"]}
            )

        assert result.isError is not True
        payload = _content_to_dict(result)
        assert len(payload["advisories"]) == 1
        assert payload["advisories"][0]["vuln_id"] == "CVE-2023-00001"
        errors = payload["query_errors"]
        assert [e["id"] for e in errors] == ["CVE-DOES-NOT-EXIST"]

    async def test_neither_packages_nor_vuln_ids_is_a_tool_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise AssertionError("OSV.dev should not be called")

        fake = FakeHy3Client(replies=[])
        server = build_server(fake, osv_client=_osv_client(handler))

        async with create_connected_server_and_client_session(server._mcp_server) as session:
            result = await session.call_tool("vuln_intel", {})

        assert result.isError is True
        assert fake.calls == []

    async def test_package_missing_name_key_is_a_descriptive_tool_error(self) -> None:
        # A malformed packages entry must not surface as a bare KeyError --
        # the judge calling this tool needs to know which key is missing.
        def handler(request: httpx.Request) -> httpx.Response:
            raise AssertionError("OSV.dev should not be called")

        fake = FakeHy3Client(replies=[])
        server = build_server(fake, osv_client=_osv_client(handler))

        async with create_connected_server_and_client_session(server._mcp_server) as session:
            result = await session.call_tool("vuln_intel", {"packages": [{"ecosystem": "PyPI"}]})

        assert result.isError is True
        (block,) = result.content
        assert isinstance(block, TextContent)
        # A bare KeyError's str() is just the quoted key ("'name'"), which
        # would ALSO satisfy a naive "'name' in text" check -- assert the
        # message is a real sentence naming the key, not that opaque repr.
        assert block.text != "Error executing tool vuln_intel: 'name'"
        assert "required" in block.text
        assert "name" in block.text
        assert fake.calls == []
