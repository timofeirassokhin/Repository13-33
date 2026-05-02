"""Handler для команды /idea — записывает идею в Twenty CRM как Idea."""
from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logger = logging.getLogger(__name__)


HELP_TEXT = (
    "Сохрани идею для контента 13-33:\n"
    "  `/idea твой текст здесь`\n\n"
    "Producer-агент возьмёт её в обработку — определит Direction/Topic, "
    "сгенерирует драфты под каналы, ты ревьюишь и публикуем."
)


async def idea_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    msg = update.message
    if not user or not msg or not msg.text:
        return

    # Извлекаем текст после /idea
    text = msg.text.strip()
    if text.startswith("/idea"):
        text = text[len("/idea"):].strip()

    if not text:
        await msg.reply_text(HELP_TEXT, parse_mode="Markdown")
        return

    twenty = context.bot_data.get("twenty")
    if twenty is None:
        await msg.reply_text(
            "⚠️ Twenty CRM пока не подключён к боту. Скажи Тимофею."
        )
        return

    try:
        result = await twenty.create_idea(
            description=text,
            telegram_user_id=user.id,
            source="telegram_bot",
        )
        idea_id = result.get("id", "?")
        idea_name = result.get("name", "")
        await msg.reply_text(
            f"✓ Сохранил идею.\n"
            f"📌 *{idea_name}*\n"
            f"`{idea_id}`\n\n"
            f"Producer-агент возьмёт её в обработку.",
            parse_mode="Markdown",
        )
        logger.info("Idea created: %s by user %d", idea_id, user.id)
    except Exception as e:
        logger.exception("Failed to create idea")
        await msg.reply_text(f"❌ Ошибка сохранения: {e}")


def register(app: Application) -> None:  # type: ignore[type-arg]
    app.add_handler(CommandHandler("idea", idea_handler))
