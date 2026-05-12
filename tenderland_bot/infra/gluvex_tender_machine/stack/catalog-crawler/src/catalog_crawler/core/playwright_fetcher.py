"""PlaywrightFetcher — headless Chromium для JS-heavy и anti-bot защищённых сайтов.

API совместим с обычным Fetcher (метод `get(url) -> str`), drop-in замена.

Особенности:
  - блокирует загрузку изображений/css/шрифтов → экономит трафик (важно для residential proxy)
  - playwright-stealth скрывает navigator.webdriver и другие fingerprint-маркеры
  - один browser context на всю сессию (faster чем создавать каждый раз)
  - поддерживает HTTP proxy через PROXY_URL env (например IPRoyal residential)
"""
from __future__ import annotations

import asyncio
import os
import time
from typing import Any

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from catalog_crawler.settings import settings


_last_call_ts = 0.0
_lock = asyncio.Lock()


async def _rate_limit(min_interval: float):
    global _last_call_ts
    async with _lock:
        now = time.monotonic()
        delta = now - _last_call_ts
        if delta < min_interval:
            await asyncio.sleep(min_interval - delta)
        _last_call_ts = time.monotonic()


class PlaywrightFetcher:
    """Drop-in замена Fetcher через headless Chromium."""

    def __init__(
        self,
        base_url: str = "",
        user_agent: str | None = None,
        extra_headers: dict[str, str] | None = None,
        proxy_url: str | None = None,
        rate_limit_seconds: float = 1.0,
        block_assets: bool = True,
        wait_until: str = "domcontentloaded",
        page_timeout_ms: int = 60000,
    ):
        self.base_url = base_url
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
        )
        self.extra_headers = extra_headers or {}
        self.proxy_url = proxy_url or os.environ.get("PROXY_URL") or None
        self.rate_limit_seconds = rate_limit_seconds
        self.block_assets = block_assets
        self.wait_until = wait_until
        self.page_timeout_ms = page_timeout_ms

        self._pw = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    async def __aenter__(self) -> "PlaywrightFetcher":
        self._pw = await async_playwright().start()

        launch_kwargs: dict[str, Any] = {
            "headless": True,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        }
        if self.proxy_url:
            # формат: http://user:pass@host:port
            launch_kwargs["proxy"] = {"server": self.proxy_url}

        self._browser = await self._pw.chromium.launch(**launch_kwargs)

        ctx_kwargs: dict[str, Any] = {
            "user_agent": self.user_agent,
            "viewport": {"width": 1920, "height": 1080},
            "locale": "en-US",
            "extra_http_headers": {
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Sec-Ch-Ua": '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
                **self.extra_headers,
            },
            # стелс — скрыть webdriver flag
            "java_script_enabled": True,
        }
        self._context = await self._browser.new_context(**ctx_kwargs)

        # блокируем тяжёлые ассеты (важно для трафика когда proxy)
        if self.block_assets:
            await self._context.route(
                "**/*",
                lambda route: (
                    route.abort()
                    if route.request.resource_type in ("image", "stylesheet", "font", "media")
                    else route.continue_()
                ),
            )

        # stealth — patch fingerprint
        try:
            from playwright_stealth import stealth_async
            # context-уровневый stealth — патчит будущие страницы автоматически
            # но в новых версиях это работает per-page
            self._stealth_async = stealth_async
        except ImportError:
            self._stealth_async = None

        return self

    async def __aexit__(self, *_):
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()

    async def get(self, url: str) -> str:
        """Загружает страницу и возвращает HTML после JS-рендеринга."""
        await _rate_limit(self.rate_limit_seconds)
        if self._context is None:
            raise RuntimeError("PlaywrightFetcher not in context (use 'async with')")

        page: Page = await self._context.new_page()
        try:
            if self._stealth_async:
                try:
                    await self._stealth_async(page)
                except Exception:
                    pass  # best-effort
            response = await page.goto(url, wait_until=self.wait_until, timeout=self.page_timeout_ms)
            if response is None:
                raise RuntimeError(f"no response for {url}")
            status = response.status
            if status >= 400:
                raise RuntimeError(f"HTTP {status} for {url}")
            # дать challenge JS шанс сработать (DataDome / Cloudflare иногда заменяет HTML после load)
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass  # networkidle может никогда не наступить — это ok, продолжаем с тем что есть
            html = await page.content()
            return html
        finally:
            await page.close()
