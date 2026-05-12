"""@gluvexlibrary_bot entry point.

Aiogram 3 dispatcher с aiohttp-сессией, прокинутой через socks5://warp:1080
(прямой outbound к api.telegram.org с RU-VPS закрыт).
"""
from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.types import TelegramObject, Update

from .db import DB
from .handlers import common as common_handlers
from .handlers import search as search_handlers
from .intent import IntentParser
from .settings import Settings
from .storage import Storage


log = logging.getLogger("library_bot")


class AccessMiddleware(BaseMiddleware):
    """Whitelist user IDs (если ALLOWED_IDS задан). Пусто = разрешено всем."""
    def __init__(self, allowed: set[int]):
        self._allowed = allowed

    async def __call__(self, handler, event: TelegramObject, data):
        # обходим всё кроме Updates с user_id
        if not self._allowed:
            return await handler(event, data)
        user_id: int | None = None
        if isinstance(event, Update):
            if event.message and event.message.from_user:
                user_id = event.message.from_user.id
            elif event.callback_query and event.callback_query.from_user:
                user_id = event.callback_query.from_user.id
        if user_id is None or user_id in self._allowed:
            return await handler(event, data)
        log.warning("Access denied for user_id=%s", user_id)
        return None


class InjectMiddleware(BaseMiddleware):
    """Прокидывает db / intent_parser / storage / settings в handler data dict."""
    def __init__(self, db: DB, intent_parser: IntentParser,
                 storage: Storage, settings: Settings):
        self._db = db
        self._intent = intent_parser
        self._storage = storage
        self._settings = settings

    async def __call__(self, handler, event: TelegramObject, data):
        data["db"] = self._db
        data["intent_parser"] = self._intent
        data["storage"] = self._storage
        data["settings"] = self._settings
        return await handler(event, data)


async def main() -> None:
    settings = Settings()  # type: ignore[call-arg]
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )
    log.info(
        "starting @%s — proxy=%s db=%s minio=%s litellm=%s",
        settings.username, settings.proxy,
        f"{settings.pg_host}:{settings.pg_port}/{settings.pg_database}",
        settings.minio_endpoint, settings.litellm_base_url,
    )

    # Aiogram session через SOCKS5 (WARP sidecar)
    session = AiohttpSession(proxy=settings.proxy) if settings.proxy else AiohttpSession()
    bot = Bot(
        token=settings.token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    me = await bot.get_me()
    log.info("authorized as @%s (id=%s)", me.username, me.id)

    # core services
    db = DB(settings)
    await db.connect()
    storage = Storage(settings)

    async with IntentParser(settings) as intent_parser:
        dp = Dispatcher()

        # middlewares (order matters — outer to inner)
        dp.update.middleware(AccessMiddleware(settings.allowed_id_set))
        dp.update.middleware(InjectMiddleware(db, intent_parser, storage, settings))

        # routers
        dp.include_router(common_handlers.router)
        dp.include_router(search_handlers.router)

        try:
            log.info("starting polling")
            await dp.start_polling(bot)
        finally:
            await bot.session.close()
            await db.close()


if __name__ == "__main__":
    asyncio.run(main())
