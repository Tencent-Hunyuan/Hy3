"""OSV.dev API client — dependency/CVE vulnerability lookups.

``OSVClient`` owns an ``httpx.AsyncClient`` (injectable for tests via
``httpx.MockTransport``, mirroring hy3_client.Hy3Client's http_client seam).
``OSVVulnerability`` is a deliberately-trimmed projection of the OSV schema —
it does not attempt to model every field OSV returns, only what
intel.synthesize_advisory needs to hand Hy3.
"""

from __future__ import annotations

from types import TracebackType
from typing import Any

import httpx
import pydantic

_QUERY_PATH = "/v1/query"
_EXCERPT_LIMIT = 200


class OSVError(Exception):
    """Raised when OSV.dev returns an error response, or a queried vuln id
    does not exist."""


class OSVVulnerability(pydantic.BaseModel):
    """A trimmed projection of one OSV.dev vulnerability record."""

    id: str
    summary: str | None = None
    details: str | None = None
    aliases: list[str] = []
    severity: list[dict[str, Any]] = []
    affected_summary: str | None = None


def _summarize_range(range_entry: dict[str, Any]) -> str | None:
    events = range_entry.get("events", [])
    introduced = next((e["introduced"] for e in events if "introduced" in e), None)
    fixed = next((e["fixed"] for e in events if "fixed" in e), None)
    if fixed is not None:
        lower = introduced if introduced not in (None, "0") else None
        return f">= {lower}, < {fixed}" if lower is not None else f"< {fixed}"
    if introduced is not None:
        return f">= {introduced}"
    return None


def _summarize_affected(affected: list[dict[str, Any]]) -> str | None:
    """Build a short human-readable affected-range string from OSV's raw
    ``affected`` entries, or None if there is nothing to summarize."""
    if not affected:
        return None

    parts: list[str] = []
    for entry in affected:
        name = entry.get("package", {}).get("name", "?")
        range_descriptions = [
            desc for r in entry.get("ranges", []) if (desc := _summarize_range(r)) is not None
        ]
        if range_descriptions:
            parts.append(f"{name}: {'; '.join(range_descriptions)}")
            continue
        versions = entry.get("versions")
        if versions:
            shown = ", ".join(versions[:5])
            suffix = ", ..." if len(versions) > 5 else ""
            parts.append(f"{name}: {shown}{suffix}")
        else:
            parts.append(name)
    return "; ".join(parts)


def _parse_vuln(raw: dict[str, Any]) -> OSVVulnerability:
    return OSVVulnerability(
        id=raw["id"],
        summary=raw.get("summary"),
        details=raw.get("details"),
        aliases=raw.get("aliases", []),
        severity=raw.get("severity", []),
        affected_summary=_summarize_affected(raw.get("affected", [])),
    )


class OSVClient:
    """Thin async client for the subset of OSV.dev's API vuln_intel needs."""

    def __init__(
        self,
        *,
        http_client: httpx.AsyncClient | None = None,
        base_url: str = "https://api.osv.dev",
    ) -> None:
        self._base_url = base_url
        self._http_client = http_client if http_client is not None else httpx.AsyncClient()

    async def query_package(
        self, name: str, ecosystem: str, version: str | None = None
    ) -> list[OSVVulnerability]:
        """POST /v1/query for one package, returning its known vulnerabilities
        (an empty or absent ``vulns`` field in the response becomes [])."""
        body: dict[str, Any] = {"package": {"name": name, "ecosystem": ecosystem}}
        if version is not None:
            body["version"] = version

        response = await self._http_client.post(f"{self._base_url}{_QUERY_PATH}", json=body)
        self._raise_for_non_2xx(response)
        return [_parse_vuln(raw) for raw in response.json().get("vulns", [])]

    async def get_vuln(self, vuln_id: str) -> OSVVulnerability:
        """GET /v1/vulns/{id}. A 404 raises OSVError naming the id."""
        response = await self._http_client.get(f"{self._base_url}/v1/vulns/{vuln_id}")
        if response.status_code == 404:
            raise OSVError(f"OSV.dev vulnerability {vuln_id!r} not found (404)")
        self._raise_for_non_2xx(response)
        return _parse_vuln(response.json())

    def _raise_for_non_2xx(self, response: httpx.Response) -> None:
        if 200 <= response.status_code < 300:
            return
        raise OSVError(
            f"OSV.dev request to {response.request.url.path!r} failed with status "
            f"{response.status_code}: {response.text[:_EXCERPT_LIMIT]}"
        )

    async def aclose(self) -> None:
        await self._http_client.aclose()

    async def __aenter__(self) -> OSVClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()
