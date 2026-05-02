"""Handlers сохранения идей в Twenty.

Поддерживается:
  - команда `/idea <текст>`
  - просто текстовое сообщение без команды
  - голосовое сообщение (см. voice.py — использует helper save_idea_from_text)
"""
from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logger = logging.getLogger(__name__)


HELP_TEXT = (
    "Сохрани идею для контента 13-33:\n"
    "  `/idea твой текст`\n"
    "  или просто отправь текст без команды\n"
    "  или отправь голосовое сообщение — расшифрую и сохраню\n\n"
    "Producer-агент возьмёт идею в обработку, ты ревьюишь и публикуем."
)


async def save_idea_from_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    source: str = "telegram_bot",
) -> None:
    """Общая логика — сохранить текст как Idea и ответить пользователю."""
    user = update.effective_user
    msg = update.message
    if not user or not msg:
        return

    text = (text or "").strip()
    if not text:
        await msg.reply_text(HELP_TEXT, parse_mode="Markdown")
        return

    twenty = context.bot_data.get("twenty")
    if twenty is None:
        await msg.reply_text("⚠️ Twenty CRM пока не подключён к боту.")
        return

    try:
        result = await twenty.create_idea(
            description=text,
            telegram_user_id=user.id,
            source=source,
        )
        idea_id = result.get("id", "?")
        idea_name = result.get("name", "")
        prefix = "🎙️ " if source == "voice" else "✓ "
        await msg.reply_text(
            f"{prefix}Сохранил идею.\n"
            f"📌 *{idea_name}*\n"
            f"`{idea_id}`",
            parse_mode="Markdown",
        )
        logger.info("Idea created: %s by user %d (source=%s)", idea_id, user.id, source)
    except Exception as e:
        logger.exception("Failed to create idea")
        await msg.reply_text(f"❌ Ошибка сохранения: {e}")


async def idea_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик `/idea <текст>`."""
    msg = update.message
    if not msg or not msg.text:
        return
    text = msg.text.strip()
    if text.startswith("/idea"):
        text = text[len("/idea"):].strip()
    if not text:
        await msg.reply_text(HELP_TEXT, parse_mode="Markdown")
        return
    await save_idea_from_text(update, context, text, source="telegram_bot")


async def plain_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик любого текстового сообщения без команды — сохраняет как Idea."""
    msg = update.message
    if not msg or not msg.text:
        return
    await save_idea_from_text(update, context, msg.text, source="telegram_bot")


def register(app: Application) -> None:  # type: ignore[type-arg]
    # Команда /idea
    app.add_handler(CommandHandler("idea", idea_command_handler))
    # Любой текст без команды → тоже идея
    # NOTE: регистрируется в самом конце, чтобы не перехватывать другие command handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, plain_text_handler))
