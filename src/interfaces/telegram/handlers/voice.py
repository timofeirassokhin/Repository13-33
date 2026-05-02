"""Handler голосовых и аудио-сообщений — транскрибирует и сохраняет как Idea."""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from src.interfaces.telegram.handlers.idea import save_idea_from_text

logger = logging.getLogger(__name__)


async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message
    if not msg:
        return

    media = msg.voice or msg.audio
    if media is None:
        return

    transcribe = context.bot_data.get("transcribe")
    if transcribe is None:
        await msg.reply_text("⚠️ Транскрибация не настроена. Скажи Тимофею.")
        return

    # Скачать файл во временный путь
    try:
        await msg.reply_text("🎙️ Слушаю и расшифровываю…")
        file = await context.bot.get_file(media.file_id)
        with tempfile.TemporaryDirectory() as td:
            local_path = Path(td) / f"voice_{media.file_id}.ogg"
            await file.download_to_drive(local_path)
            text = await transcribe.transcribe(local_path)
    except Exception as e:
        logger.exception("Voice download/transcribe failed")
        await msg.reply_text(f"❌ Не получилось расшифровать: {e}")
        return

    if not text or len(text.strip()) < 3:
        await msg.reply_text(
            "Не распознал речь. Попробуй ещё раз — говори чётче, не прячь микрофон."
        )
        return

    # Сохранить как Idea
    await save_idea_from_text(update, context, text, source="voice")


def register(app: Application) -> None:  # type: ignore[type-arg]
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, voice_handler))
