from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiohttp import web

if TYPE_CHECKING:
    from src.config import Settings
    from src.services.google_auth import GoogleAuthService

logger = logging.getLogger(__name__)

SUCCESS_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Авторизация</title>
<style>body{font-family:sans-serif;display:flex;justify-content:center;
align-items:center;height:100vh;margin:0;background:#f0f2f5}
.card{background:white;padding:40px;border-radius:12px;text-align:center;
box-shadow:0 2px 10px rgba(0,0,0,.1)}h1{color:#2ecc71}
</style></head><body><div class="card"><h1>&#10004; Успешно!</h1>
<p>Авторизация прошла успешно. Вернитесь в Telegram.</p></div></body></html>"""

ERROR_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Ошибка</title>
<style>body{font-family:sans-serif;display:flex;justify-content:center;
align-items:center;height:100vh;margin:0;background:#f0f2f5}
.card{background:white;padding:40px;border-radius:12px;text-align:center;
box-shadow:0 2px 10px rgba(0,0,0,.1)}h1{color:#e74c3c}
</style></head><body><div class="card"><h1>&#10008; Ошибка</h1>
<p>%s</p></div></body></html>"""


class OAuthCallbackServer:
    def __init__(self, auth_service: GoogleAuthService, settings: Settings) -> None:
        self._auth = auth_service
        self._settings = settings
        self._runner: web.AppRunner | None = None

    async def start(self) -> None:
        app = web.Application()
        app.router.add_get("/oauth/callback", self._handle_callback)
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        site = web.TCPSite(
            self._runner,
            self._settings.webhook_host,
            self._settings.webhook_port,
        )
        await site.start()
        logger.info(
            "OAuth callback server started on %s:%d",
            self._settings.webhook_host,
            self._settings.webhook_port,
        )

    async def stop(self) -> None:
        if self._runner:
            await self._runner.cleanup()
            logger.info("OAuth callback server stopped")

    async def _handle_callback(self, request: web.Request) -> web.Response:
        code = request.query.get("code")
        state = request.query.get("state")

        if not code or not state:
            return web.Response(
                text=ERROR_HTML % "Отсутствуют параметры авторизации.",
                content_type="text/html",
                status=400,
            )

        try:
            await self._auth.handle_callback(code, state)
            return web.Response(
                text=SUCCESS_HTML,
                content_type="text/html",
            )
        except Exception as e:
            logger.exception("OAuth callback error")
            return web.Response(
                text=ERROR_HTML % f"Ошибка авторизации: {e}",
                content_type="text/html",
                status=500,
            )
