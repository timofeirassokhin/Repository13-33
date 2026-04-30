from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from src.agent.intent import Intent, ParsedCommand
from src.models.common import UserContext

logger = logging.getLogger(__name__)

# Conversation states for /event
TITLE, TIME_START, TIME_END, DESCRIPTION, CONFIRM = range(5)


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


# --- /event conversation ---

async def event_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return ConversationHandler.END
    await update.message.reply_text("Создаём событие. Введите название:")
    return TITLE


async def event_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text:
        return ConversationHandler.END
    context.user_data["event_title"] = update.message.text  # type: ignore[index]
    await update.message.reply_text(
        "Когда начинается? (формат: ДД.ММ.ГГГГ ЧЧ:ММ)\n"
        "Например: 25.12.2025 14:00"
    )
    return TIME_START


async def event_time_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text:
        return ConversationHandler.END
    try:
        dt = datetime.strptime(update.message.text.strip(), "%d.%m.%Y %H:%M")
        dt = dt.replace(tzinfo=timezone.utc)
        context.user_data["event_start"] = dt.isoformat()  # type: ignore[index]
    except ValueError:
        await update.message.reply_text(
            "Неверный формат. Используйте: ДД.ММ.ГГГГ ЧЧ:ММ"
        )
        return TIME_START
    await update.message.reply_text(
        "Когда заканчивается? (формат: ДД.ММ.ГГГГ ЧЧ:ММ)\n"
        "Или введите длительность в минутах (например: 60)"
    )
    return TIME_END


async def event_time_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text:
        return ConversationHandler.END
    text = update.message.text.strip()
    start = datetime.fromisoformat(context.user_data["event_start"])  # type: ignore[index]
    try:
        if text.isdigit():
            dt = start + timedelta(minutes=int(text))
        else:
            dt = datetime.strptime(text, "%d.%m.%Y %H:%M")
            dt = dt.replace(tzinfo=timezone.utc)
        context.user_data["event_end"] = dt.isoformat()  # type: ignore[index]
    except ValueError:
        await update.message.reply_text("Неверный формат. Попробуйте снова.")
        return TIME_END

    await update.message.reply_text(
        "Описание (или отправьте /skip):"
    )
    return DESCRIPTION


async def event_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return ConversationHandler.END
    text = update.message.text or ""
    if text.strip() == "/skip":
        text = ""
    context.user_data["event_desc"] = text  # type: ignore[index]

    start = datetime.fromisoformat(context.user_data["event_start"]).strftime("%d.%m.%Y %H:%M")  # type: ignore[index]
    end = datetime.fromisoformat(context.user_data["event_end"]).strftime("%d.%m.%Y %H:%M")  # type: ignore[index]

    await update.message.reply_text(
        f"<b>Подтвердите событие:</b>\n\n"
        f"Название: {context.user_data['event_title']}\n"  # type: ignore[index]
        f"Начало: {start}\n"
        f"Конец: {end}\n"
        f"Описание: {text or '—'}\n\n"
        f"Создать? (да/нет)",
        parse_mode="HTML",
    )
    return CONFIRM


async def event_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text:
        return ConversationHandler.END

    if update.message.text.strip().lower() not in ("да", "yes", "д", "y"):
        await update.message.reply_text("Создание события отменено.")
        return ConversationHandler.END

    user_ctx = await _build_user_context(update, context)
    dispatcher = context.bot_data["dispatcher"]

    command = ParsedCommand(
        intent=Intent.CREATE_EVENT,
        params={
            "summary": context.user_data["event_title"],  # type: ignore[index]
            "start": context.user_data["event_start"],  # type: ignore[index]
            "end": context.user_data["event_end"],  # type: ignore[index]
            "description": context.user_data.get("event_desc", ""),  # type: ignore[union-attr]
        },
    )
    result = await dispatcher.dispatch(command, user_ctx)
    await update.message.reply_text(result, parse_mode="HTML")
    return ConversationHandler.END


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message:
        await update.message.reply_text("Отменено.")
    return ConversationHandler.END


# --- /agenda ---

async def agenda_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    user_ctx = await _build_user_context(update, context)
    dispatcher = context.bot_data["dispatcher"]

    args = context.args or []
    days = int(args[0]) if args and args[0].isdigit() else 1

    command = ParsedCommand(
        intent=Intent.VIEW_AGENDA,
        params={"days_ahead": days},
    )
    result = await dispatcher.dispatch(command, user_ctx)
    await update.message.reply_text(result, parse_mode="HTML")


def register(app: Application) -> None:  # type: ignore[type-arg]
    conv = ConversationHandler(
        entry_points=[CommandHandler("event", event_start)],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_title)],
            TIME_START: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_time_start)],
            TIME_END: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_time_end)],
            DESCRIPTION: [
                MessageHandler(filters.TEXT, event_description),
            ],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_confirm)],
        },
        fallbacks=[CommandHandler("cancel", cancel_handler)],
    )
    app.add_handler(conv)
    app.add_handler(CommandHandler("agenda", agenda_handler))
