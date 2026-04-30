from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logger = logging.getLogger(__name__)

HELP_TEXT = """<b>Личный помощник — команды:</b>

<b>Авторизация</b>
/login — подключить Google аккаунт
/logout — отключить Google аккаунт

<b>Календарь</b>
/event — создать событие
/agenda [дней] — показать расписание
/remind — установить напоминание

<b>Заметки</b>
/note — создать заметку
/notes — список заметок
/search_notes — поиск по заметкам

<b>Файлы</b>
/sort [folder_id] — сортировать файлы
/rules — правила сортировки
/add_rule — добавить правило

/help — эта справка"""


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.message:
        return

    user_repo = context.bot_data["user_repo"]
    is_auth = await user_repo.is_authenticated(user.id)
    status = "подключён" if is_auth else "не подключён"

    await update.message.reply_text(
        f"Привет, {user.first_name}!\n\n"
        f"Я — твой личный помощник. Управляю календарём, заметками и файлами.\n\n"
        f"Google аккаунт: <b>{status}</b>\n\n"
        f"Используй /help для списка команд.",
        parse_mode="HTML",
    )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(HELP_TEXT, parse_mode="HTML")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling update: %s", context.error, exc_info=context.error)
    if isinstance(update, Update) and update.message:
        await update.message.reply_text(
            "Произошла внутренняя ошибка. Попробуйте позже."
        )


def register(app: Application) -> None:  # type: ignore[type-arg]
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_error_handler(error_handler)
