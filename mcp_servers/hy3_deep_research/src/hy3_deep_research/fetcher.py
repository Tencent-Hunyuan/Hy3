"""Safe, bounded extraction of public HTTP(S) documents."""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup

from .models import FetchedDocument


class FetchError(RuntimeError):
    """Raised when a document cannot be fetched or extracted."""


class WebFetcher:
    def __init__(
        self,
        *,
        timeout_seconds: float = 20.0,
        max_chars: int = 20_000,
        allow_private_urls: bool = False,
        max_concurrency: int = 4,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._max_chars = max_chars
        self._allow_private_urls = allow_private_urls
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def fetch(self, url: str) -> FetchedDocument:
        async with self._semaphore:
            return await self._fetch(url)

    async def _fetch(self, url: str) -> FetchedDocument:
        headers = {
            "User-Agent": "Hy3DeepResearchMCP/0.1 (+https://github.com/Tencent-Hunyuan/Hy3)",
            "Accept": "text/html,application/xhtml+xml,text/plain,application/json;q=0.9,*/*;q=0.1",
        }
        timeout = httpx.Timeout(self._timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
            current_url = url
            for _ in range(6):
                await self._validate_public_url(current_url)
                try:
                    async with client.stream(
                        "GET", current_url, follow_redirects=False
                    ) as response:
                        if response.is_redirect:
                            location = response.headers.get("location")
                            if not location:
                                raise FetchError(
                                    "redirect response has no Location header"
                                )
                            current_url = urljoin(current_url, location)
                            continue
                        response.raise_for_status()
                        content_type = response.headers.get("content-type", "").lower()
                        if not any(
                            supported in content_type
                            for supported in ("text/", "html", "json", "xml")
                        ):
                            raise FetchError(
                                f"unsupported content type: {content_type or 'unknown'}"
                            )
                        raw = await self._read_bounded(response)
                        encoding = response.encoding or "utf-8"
                        text = raw.decode(encoding, errors="replace")
                except httpx.HTTPError as exc:
                    raise FetchError(f"request failed: {type(exc).__name__}") from exc

                title, content = self._extract(text, content_type, current_url)
                if not content.strip():
                    raise FetchError("page contains no extractable text")
                return FetchedDocument(
                    title=title,
                    url=current_url,
                    content=content[: self._max_chars],
                    content_type=content_type,
                )
        raise FetchError("too many redirects")

    async def _read_bounded(self, response: httpx.Response) -> bytes:
        max_bytes = max(self._max_chars * 4, 100_000)
        chunks: list[bytes] = []
        size = 0
        async for chunk in response.aiter_bytes():
            size += len(chunk)
            if size > max_bytes:
                remaining = max_bytes - (size - len(chunk))
                if remaining > 0:
                    chunks.append(chunk[:remaining])
                break
            chunks.append(chunk)
        return b"".join(chunks)

    async def _validate_public_url(self, url: str) -> None:
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise FetchError("only absolute HTTP(S) URLs are supported")
        if parsed.username or parsed.password:
            raise FetchError("URLs containing credentials are not supported")
        if self._allow_private_urls:
            return

        try:
            addresses = await asyncio.to_thread(
                socket.getaddrinfo,
                parsed.hostname,
                parsed.port or (443 if parsed.scheme == "https" else 80),
                type=socket.SOCK_STREAM,
            )
        except socket.gaierror as exc:
            raise FetchError("hostname could not be resolved") from exc
        for address in addresses:
            ip = ipaddress.ip_address(address[4][0])
            if not ip.is_global:
                raise FetchError(
                    "private, loopback, link-local, and reserved URLs are blocked"
                )

    def _extract(self, text: str, content_type: str, url: str) -> tuple[str, str]:
        if "html" not in content_type and "xhtml" not in content_type:
            return url, text.strip()[: self._max_chars]

        soup = BeautifulSoup(text, "html.parser")
        for tag in soup(
            ["script", "style", "noscript", "svg", "nav", "footer", "form"]
        ):
            tag.decompose()
        title = soup.title.get_text(" ", strip=True) if soup.title else url
        root = soup.find("article") or soup.find("main") or soup.body or soup
        content = "\n".join(root.stripped_strings)
        return title, content[: self._max_chars]
