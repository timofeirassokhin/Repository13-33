from __future__ import annotations

import asyncio
import logging
import sys

from src.config import Settings
from src.logger import setup_logging
from src.db.connection import Database
from src.db.migrations import run_migrations
from src.db.repositories.user_repo import UserRepository
from src.services.google_auth import GoogleAuthService
from src.services.calendar_service import CalendarService
from src.services.notes_service import NotesService
from src.services.file_sorter_service import FileSorterService
from src.services.twenty import TwentyClient
from src.services.transcribe import TranscribeService
from src.services.llm import LLMClient
from src.agent.dispatcher import AgentDispatcher
from src.interfaces.telegram.bot import TelegramBot
from src.interfaces.webhook.oauth_callback import OAuthCallbackServer

logger = logging.getLogger(__name__)


async def main() -> None:
    # Config
    settings = Settings()
    setup_logging(settings)
    logger.info("Starting Personal Assistant Bot...")

    # Database
    db = Database(settings)
    await db.connect()
    await run_migrations(db)

    # Repositories
    user_repo = UserRepository(db)

    # Services
    auth_service = GoogleAuthService(db, settings)
    calendar_service = CalendarService(db, settings, auth_service)
    notes_service = NotesService(db, settings, auth_service)
    file_sorter_service = FileSorterService(db, settings, auth_service)
    twenty = TwentyClient(settings) if settings.twenty_api_key.get_secret_value() else None
    if twenty:
        logger.info("TwentyClient enabled (URL=%s)", settings.twenty_api_url)
    else:
        logger.warning("TwentyClient disabled (TWENTY_API_KEY не задан)")

    transcribe = TranscribeService(settings) if settings.whisper_url else None
    if transcribe:
        logger.info("TranscribeService enabled (URL=%s)", settings.whisper_url)
    else:
        logger.warning("TranscribeService disabled (WHISPER_URL не задан)")

    llm = LLMClient(settings) if settings.litellm_master_key.get_secret_value() else None
    if llm:
        logger.info("LLMClient enabled (URL=%s)", settings.litellm_url)
    else:
        logger.warning("LLMClient disabled (LITELLM_MASTER_KEY не задан)")

    # Agent dispatcher
    dispatcher = AgentDispatcher(
        auth_service=auth_service,
        calendar_service=calendar_service,
        notes_service=notes_service,
        file_sorter_service=file_sorter_service,
    )

    # Interfaces
    bot = TelegramBot(
        settings, dispatcher, user_repo,
        twenty=twenty, transcribe=transcribe, llm=llm,
    )
    oauth_server = OAuthCallbackServer(auth_service, settings)

    # Start
    await oauth_server.start()
    await bot.start()
    logger.info("Bot is running. Press Ctrl+C to stop.")

    # Wait for shutdown signal
    stop_event = asyncio.Event()

    if sys.platform != "win32":
        import signal
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop_event.set)
        await stop_event.wait()
    else:
        # On Windows, signal handlers don't work in asyncio
        # The KeyboardInterrupt will be caught below
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            pass

    # Shutdown
    logger.info("Shutting down...")
    await bot.stop()
    await oauth_server.stop()
    if twenty:
        await twenty.close()
    if transcribe:
        await transcribe.close()
    if llm:
        await llm.close()
    await db.disconnect()
    logger.info("Goodbye!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
