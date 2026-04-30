from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from src.agent.intent import Intent, ParsedCommand
from src.models.common import UserContext

logger = logging.getLogger(__name__)

# Conversation states for /note
NOTE_TITLE, NOTE_CONTENT, NOTE_TAGS, NOTE_CONFIRM = range(4)


async def _build_user_context(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> UserContext:
    user = update.effective_user
    chat = update.effective_chat
    user_repo = context.bot_data["user_repo"]
    is_auth = await user_repo.is_authenticated(user.id) if user else False
    return UserContext(
        telegram_user_id=user.id if user else 0,
        telegram_chat_id=chat.id if chat else 0,
        google_authenticated=is_auth,
    )


# --- /note conversation ---

async def note_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return ConversationHandler.END
    await update.message.reply_text("Создаём заметку. Введите заголовок:")
    return NOTE_TITLE


async def note_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text:
        return ConversationHandler.END
    context.user_data["note_title"] = update.message.text  # type: ignore[index]
    await update.message.reply_text("Введите текст заметки (или /skip):")
    return NOTE_CONTENT


async def note_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return ConversationHandler.END
    text = update.message.text or ""
    if text.strip() == "/skip":
        text = ""
    context.user_data["note_content"] = text  # type: ignore[index]
    await update.message.reply_text(
        "Введите теги через пробел (или /skip):\n"
        "Например: работа проект важное"
    )
    return NOTE_TAGS


async def note_tags(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return ConversationHandler.END
    text = update.message.text or ""
    if text.strip() == "/skip":
        tags: list[str] = []
    else:
        tags = text.strip().split()
    context.user_data["note_tags"] = tags  # type: ignore[index]

    tags_str = ", ".join(tags) if tags else "—"
    content_preview = context.user_data.get("note_content", "")[:100] or "—"  # type: ignore[union-attr]

    await update.message.reply_text(
        f"<b>Подтвердите заметку:</b>\n\n"
        f"Заголовок: {context.user_data['note_title']}\n"  # type: ignore[index]
        f"Теги: {tags_str}\n"
        f"Содержание: {content_preview}\n\n"
        f"Создать? (да/нет)",
        parse_mode="HTML",
    )
    return NOTE_CONFIRM


async def note_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text:
        return ConversationHandler.END

    if update.message.text.strip().lower() not in ("да", "yes", "д", "y"):
        await update.message.reply_text("Создание заметки отменено.")
        return ConversationHandler.END

    user_ctx = await _build_user_context(update, context)
    dispatcher = context.bot_data["dispatcher"]

    command = ParsedCommand(
        intent=Intent.CREATE_NOTE,
        params={
            "title": context.user_data["note_title"],  # type: ignore[index]
            "content": context.user_data.get("note_content", ""),  # type: ignore[union-attr]
            "tags": context.user_data.get("note_tags", []),  # type: ignore[union-attr]
        },
    )
    result = await dispatcher.dispatch(command, user_ctx)
    await update.message.reply_text(result, parse_mode="HTML")
    return ConversationHandler.END


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message:
        await update.message.reply_text("Отменено.")
    return ConversationHandler.END


# --- /notes ---

async def notes_list_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    user_ctx = await _build_user_context(update, context)
    dispatcher = context.bot_data["dispatcher"]

    command = ParsedCommand(intent=Intent.LIST_NOTES)
    result = await dispatcher.dispatch(command, user_ctx)
    await update.message.reply_text(result, parse_mode="HTML")


# --- /search_notes ---

async def search_notes_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    user_ctx = await _build_user_context(update, context)
    dispatcher = context.bot_data["dispatcher"]

    args = context.args or []
    query_text = " ".join(args) if args else ""

    if not query_text:
        await update.message.reply_text("Использование: /search_notes <запрос>")
        return

    command = ParsedCommand(
        intent=Intent.SEARCH_NOTES,
        params={"query": query_text},
    )
    result = await dispatcher.dispatch(command, user_ctx)
    await update.message.reply_text(result, parse_mode="HTML")


def register(app: Application) -> None:  # type: ignore[type-arg]
    conv = ConversationHandler(
        entry_points=[CommandHandler("note", note_start)],
        states={
            NOTE_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, note_title)],
            NOTE_CONTENT: [MessageHandler(filters.TEXT, note_content)],
            NOTE_TAGS: [MessageHandler(filters.TEXT, note_tags)],
            NOTE_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, note_confirm)],
        },
        fallbacks=[CommandHandler("cancel", cancel_handler)],
    )
    app.add_handler(conv)
    app.add_handler(CommandHandler("notes", notes_list_handler))
    app.add_handler(CommandHandler("search_notes", search_notes_handler))
