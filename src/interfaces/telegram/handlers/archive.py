"""Handler /archive — добавить текст в MemPalace (server-side архив 13-33).

Использование:
  /archive                          — справка + список wings
  /archive <wing> <текст>           — записать в указанный wing
  /archive misc какая-то заметка    — пример

Текст-документы из Telegram (TXT/MD) — handled at voice/document level позже.
PDF/DOCX — через bulk upload script (Phase 5I.4).
"""
from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from src.services.mempalace import WINGS

logger = logging.getLogger(__name__)


HELP = (
    "Записать в архив 13-33 (MemPalace):\n"
    "  `/archive <wing> <текст>`\n\n"
    "Wings:\n"
    "  • `books` — книги полным текстом\n"
    "  • `articles` — научные статьи и исследования\n"
    "  • `13-33main` — проверенное ядро 13-33\n"
    "  • `13-33pubs` — опубликованные посты\n"
    "  • `13-33scenarios` — сценарии (видео/подкасты)\n"
    "  • `13-33interviews` — интервью\n"
    "  • `13-33drafts` — драфты в работе\n"
    "  • `misc` — прочее\n\n"
    "Пример: `/archive misc заметка про практики осознанности`"
)


async def archive_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message
    if not msg or not msg.text:
        return

    args = msg.text.replace("/archive", "", 1).strip()
    if not args:
        await msg.reply_text(HELP, parse_mode="Markdown")
        return

    parts = args.split(maxsplit=1)
    if len(parts) < 2:
        await msg.reply_text(
            f"Не хватает текста. Формат: `/archive <wing> <текст>`\n\n{HELP}",
            parse_mode="Markdown",
        )
        return

    wing = parts[0]
    content = parts[1].strip()

    if wing not in WINGS:
        await msg.reply_text(
            f"Wing `{wing}` не в списке. Доступные: {', '.join(f'`{w}`' for w in WINGS)}",
            parse_mode="Markdown",
        )
        return

    mempalace = context.bot_data.get("mempalace")
    if mempalace is None:
        await msg.reply_text("⚠️ MemPalace не подключён.")
        return

    try:
        result = await mempalace.add_drawer(
            content=content,
            wing=wing,
            room="default",
            added_by=f"tg_user_{update.effective_user.id if update.effective_user else 'unknown'}",
        )
        first_line = content.split("\n", 1)[0][:60]
        await msg.reply_text(
            f"📚 Сохранил в `{wing}`\n"
            f"id: `{result['id']}`\n"
            f"_{first_line}…_",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.exception("Archive failed")
        await msg.reply_text(f"❌ {e}")


def register(app: Application) -> None:  # type: ignore[type-arg]
    app.add_handler(CommandHandler("archive", archive_handler))
