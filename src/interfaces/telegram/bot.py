from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from telegram.ext import Application, ApplicationBuilder

if TYPE_CHECKING:
    from src.agent.dispatcher import AgentDispatcher
    from src.config import Settings
    from src.db.repositories.user_repo import UserRepository
    from src.services.llm import LLMClient
    from src.services.mempalace import MempalaceClient
    from src.services.transcribe import TranscribeService
    from src.services.twenty import TwentyClient

logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(
        self,
        settings: Settings,
        dispatcher: AgentDispatcher,
        user_repo: UserRepository,
        twenty: TwentyClient | None = None,
        transcribe: TranscribeService | None = None,
        llm: LLMClient | None = None,
        mempalace: MempalaceClient | None = None,
    ) -> None:
        self._settings = settings
        self._dispatcher = dispatcher
        self._user_repo = user_repo
        self._twenty = twenty
        self._transcribe = transcribe
        self._llm = llm
        self._mempalace = mempalace
        self._app: Application | None = None  # type: ignore[type-arg]

    async def start(self) -> None:
        builder = (
            ApplicationBuilder()
            .token(self._settings.telegram_bot_token.get_secret_value())
        )

        # Прокси для outbound к api.telegram.org (нужен на хостингах,
        # где прямой доступ к Telegram заблокирован).
        proxy = self._settings.telegram_proxy
        if proxy:
            logger.info("Telegram bot will use proxy: %s", proxy)
            builder = builder.proxy(proxy).get_updates_proxy(proxy)

        self._app = builder.build()

        # Store shared objects in bot_data
        self._app.bot_data["dispatcher"] = self._dispatcher
        self._app.bot_data["settings"] = self._settings
        self._app.bot_data["user_repo"] = self._user_repo
        self._app.bot_data["twenty"] = self._twenty
        self._app.bot_data["transcribe"] = self._transcribe
        self._app.bot_data["llm"] = self._llm
        self._app.bot_data["mempalace"] = self._mempalace

        self._register_handlers()

        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling()  # type: ignore[union-attr]
        logger.info("Telegram bot started")

    async def stop(self) -> None:
        if self._app and self._app.updater:
            await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()
            logger.info("Telegram bot stopped")

    def _register_handlers(self) -> None:
        assert self._app is not None
        from src.interfaces.telegram.handlers import (
            archive, auth, calendar, common, draft, files, idea, iterate, library,
            listing, notes, voice,
        )

        common.register(self._app)
        auth.register(self._app)
        calendar.register(self._app)
        notes.register(self._app)
        files.register(self._app)
        voice.register(self._app)
        draft.register(self._app)
        iterate.register(self._app)
        listing.register(self._app)
        archive.register(self._app)
        library.register(self._app)
        # idea — последним, так как ловит plain text без команд
        idea.register(self._app)
