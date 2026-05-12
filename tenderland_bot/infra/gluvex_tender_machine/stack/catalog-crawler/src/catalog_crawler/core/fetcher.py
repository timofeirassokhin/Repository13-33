"""HTTP fetcher с retry и rate-limit."""
from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from catalog_crawler.settings import settings


_last_call_ts = 0.0
_lock = asyncio.Lock()


async def _enforce_rate_limit():
    """Простой global rate-limit (можно потом сделать per-host)."""
    global _last_call_ts
    async with _lock:
        min_interval = 1.0 / settings.rate_limit_rps
        now = time.monotonic()
        delta = now - _last_call_ts
        if delta < min_interval:
            await asyncio.sleep(min_interval - delta)
        _last_call_ts = time.monotonic()


class Fetcher:
    def __init__(self, base_url: str = "", user_agent: str | None = None, extra_headers: dict[str, str] | None = None):
        self.base_url = base_url
        self.user_agent = user_agent or settings.user_agent
        self.extra_headers = extra_headers or {}
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "Fetcher":
        headers = {
            "User-Agent": self.user_agent,
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        headers.update(self.extra_headers)
        self._client = httpx.AsyncClient(
            timeout=settings.request_timeout,
            headers=headers,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, *_):
        if self._client is not None:
            await self._client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=15),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True,
    )
    async def get(self, url: str) -> str:
        if self._client is None:
            raise RuntimeError("Fetcher not in context")
        await _enforce_rate_limit()
        r = await self._client.get(url)
        r.raise_for_status()
        return r.text
