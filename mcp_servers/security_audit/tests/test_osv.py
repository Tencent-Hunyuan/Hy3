"""Tests for OSVClient: request shape, response parsing, and error handling
against OSV.dev — all via httpx.MockTransport (zero network).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from hy3_security_mcp.osv import OSVClient, OSVError, OSVVulnerability


def _make_client(handler: Callable[[httpx.Request], httpx.Response]) -> OSVClient:
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    return OSVClient(http_client=http_client)


def _vuln_json(vuln_id: str = "GHSA-xxxx-xxxx-xxxx") -> dict[str, Any]:
    return {
        "id": vuln_id,
        "summary": "Improper input validation",
        "details": "A crafted redirect can leak the Proxy-Authorization header.",
        "aliases": ["CVE-2023-12345"],
        "severity": [{"type": "CVSS_V3", "score": "7.5"}],
        "affected": [
            {
                "package": {"name": "requests", "ecosystem": "PyPI"},
                "ranges": [
                    {
                        "type": "ECOSYSTEM",
                        "events": [{"introduced": "0"}, {"fixed": "2.31.0"}],
                    }
                ],
            }
        ],
    }


class TestQueryPackage:
    async def test_posts_expected_body_with_version(self) -> None:
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["path"] = request.url.path
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json={"vulns": [_vuln_json()]})

        client = _make_client(handler)

        await client.query_package("requests", "PyPI", "2.6.0")

        assert captured["path"] == "/v1/query"
        assert captured["body"] == {
            "package": {"name": "requests", "ecosystem": "PyPI"},
            "version": "2.6.0",
        }

    async def test_version_less_query_omits_version_key(self) -> None:
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json={"vulns": []})

        client = _make_client(handler)

        await client.query_package("requests", "PyPI")

        assert captured["body"] == {"package": {"name": "requests", "ecosystem": "PyPI"}}
        assert "version" not in captured["body"]

    async def test_parses_vulns_into_osv_vulnerability_list(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"vulns": [_vuln_json()]})

        client = _make_client(handler)

        vulns = await client.query_package("requests", "PyPI")

        assert len(vulns) == 1
        vuln = vulns[0]
        assert isinstance(vuln, OSVVulnerability)
        assert vuln.id == "GHSA-xxxx-xxxx-xxxx"
        assert vuln.summary == "Improper input validation"
        assert vuln.aliases == ["CVE-2023-12345"]
        assert vuln.severity == [{"type": "CVSS_V3", "score": "7.5"}]
        assert vuln.affected_summary is not None
        assert "requests" in vuln.affected_summary
        assert "2.31.0" in vuln.affected_summary

    async def test_empty_vulns_key_returns_empty_list(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"vulns": []})

        client = _make_client(handler)

        assert await client.query_package("leftpad", "npm") == []

    async def test_absent_vulns_key_returns_empty_list(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={})

        client = _make_client(handler)

        assert await client.query_package("leftpad", "npm") == []

    async def test_no_affected_data_leaves_affected_summary_none(self) -> None:
        bare = {"id": "GHSA-bare", "summary": None, "aliases": []}

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"vulns": [bare]})

        client = _make_client(handler)

        vulns = await client.query_package("leftpad", "npm")

        assert vulns[0].affected_summary is None

    async def test_500_raises_osv_error_with_status(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="internal server error")

        client = _make_client(handler)

        with pytest.raises(OSVError) as exc_info:
            await client.query_package("requests", "PyPI")

        message = str(exc_info.value)
        assert "500" in message


class TestGetVuln:
    async def test_gets_expected_path_and_parses_vuln(self) -> None:
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["method"] = request.method
            captured["path"] = request.url.path
            return httpx.Response(200, json=_vuln_json("CVE-2023-12345"))

        client = _make_client(handler)

        vuln = await client.get_vuln("CVE-2023-12345")

        assert captured["method"] == "GET"
        assert captured["path"] == "/v1/vulns/CVE-2023-12345"
        assert vuln.id == "CVE-2023-12345"
        assert vuln.details is not None and "Proxy-Authorization" in vuln.details

    async def test_404_raises_osv_error_naming_the_id(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, text="not found")

        client = _make_client(handler)

        with pytest.raises(OSVError) as exc_info:
            await client.get_vuln("CVE-9999-99999")

        assert "CVE-9999-99999" in str(exc_info.value)

    async def test_500_raises_osv_error_with_status(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="internal server error")

        client = _make_client(handler)

        with pytest.raises(OSVError) as exc_info:
            await client.get_vuln("CVE-2023-12345")

        assert "500" in str(exc_info.value)


class TestLifecycle:
    async def test_aclose_closes_the_underlying_http_client(self) -> None:
        transport = httpx.MockTransport(lambda request: httpx.Response(200, json={}))
        http_client = httpx.AsyncClient(transport=transport)
        client = OSVClient(http_client=http_client)

        await client.aclose()

        assert http_client.is_closed

    async def test_async_context_manager_closes_on_exit(self) -> None:
        transport = httpx.MockTransport(lambda request: httpx.Response(200, json={}))
        http_client = httpx.AsyncClient(transport=transport)

        async with OSVClient(http_client=http_client) as client:
            assert isinstance(client, OSVClient)

        assert http_client.is_closed
